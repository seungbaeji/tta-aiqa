# Kubernetes Deployment

## 1. Prerequisites

### 1-1. Registry pull credential

The published Risk API and KServe predictor images are private GHCR packages.
Before Argo CD syncs any overlay, the instructor provisions the non-versioned
`ghcr-pull` Docker registry Secret in the `tta-aiqa` namespace. The Secret is
cluster infrastructure, never committed to this repository or supplied to
students.

Set `TARGET_CONTEXT` to the exact context approved by the cluster operator.
The command below fails before contacting a cluster when that value is empty or
does not match the current context.

```bash
if [ -z "${TARGET_CONTEXT:-}" ]; then
  echo "TARGET_CONTEXT is required; refusing to change a cluster." >&2
  exit 1
fi
CURRENT_CONTEXT="$(kubectl config current-context)" || {
  echo "Unable to read the current Kubernetes context; refusing to continue." >&2
  exit 1
}
if [ "$CURRENT_CONTEXT" != "$TARGET_CONTEXT" ]; then
  echo "Context mismatch: expected $TARGET_CONTEXT, got $CURRENT_CONTEXT" >&2
  exit 1
fi
kubectl --context "$TARGET_CONTEXT" -n tta-aiqa \
  create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=<registry-user> \
  --docker-password=<read-packages-token>
```

The Risk API Pod and KServe Predictor both reference this Secret through
`imagePullSecrets`. Their application runtime secrets remain separate optional
projected volumes.

## 2. Image and Model Identity

### 2-1. Immutable deployment inputs

The base manifests pin published OCI image digests. The selected PVC model
subPath and the non-secret `model-identity` ConfigMap must move together. The
predictor verifies the expected model SHA-256 before it becomes ready.

The latest runtime build-input commit, multi-architecture OCI index digests, and
local image smoke results are recorded in
[`runtime-images-v2.json`](../../docs/reference/evidence/deployment/runtime-images-v2.json).
The deployment contract test rejects manifests that drift from this record or
runtime build inputs that changed after the recorded source commit.

Candidate B and rollback are Kustomize overlays. Students inspect rendered
manifests; the instructor's Argo CD workflow performs the actual sync.

## 3. Shared-cluster guardrails

The base installs a deliberately generous object-count `ResourceQuota`. It
limits accidental pod, Service, Secret, ConfigMap, and PVC growth without
requiring every KServe-managed container to declare a new CPU or memory quota.
Review these ceilings with the cluster operator before combining this namespace
with additional course workloads.

Observed overlays also install an ingress-only `NetworkPolicy` for Alloy. OTLP
traffic is accepted only from `tta-aiqa`-labelled pods in the same namespace.
The Alloy HTTP administration port remains inside the Pod and is not published
by the Service. Grafana Cloud export remains outbound and is not restricted.
The policy does not select Risk API or KServe pods, so the platform's existing
API ingress path remains unchanged.

The base includes a Traefik Ingress that connects the ClusterIP `risk-api`
Service to the cluster HTTP entrypoint. The manifest does not set a hostname.

## 4. Read-only release verification

After the platform workflow synchronizes an overlay, verify that stage without
applying or patching any resource. Use `baseline-observed` when the baseline
stage must emit live telemetry, then synchronize `candidate-b` and `rollback`.
Run the verifier with release names `baseline`, `candidate-b`, and `rollback`,
using a different output file each time.

```bash
uv run python scripts/verify_target_release.py \
  --expected-context "${TARGET_CONTEXT:?approved course context is required}" \
  --release candidate-b \
  --target-url "${TARGET_API_URL:?Risk API base URL is required}" \
  --output artifacts/reports/target-candidate-b.json
```

The verifier fails closed when the active context differs. Every cluster read
uses the explicit context and fixed `tta-aiqa` namespace. It checks the registry
Secret type, bound model PVC, selected model SHA-256 and subPath, desired OCI
index references, running platform manifest digests, rollout readiness, API
model identity, and one valid prediction. It never creates, synchronizes,
patches, or rolls back resources and never writes request features to its
report.

A passing release report does not claim that Grafana received live data. Keep
`live_telemetry_status=not_checked` until metrics, bounded logs, and the
representative trace are confirmed for the same model and UTC range.

## 5. Course MLflow

Closed-network learners connect to the cluster MLflow tracking server through
the platform-injected Ingress URL. They set `AIQA_MLFLOW_TRACKING_URI` to that
URL. They do not create a ClusterIP Service, port-forward, or tunnel, and they
do not use Compose `http://127.0.0.1:5000` as the classroom path.

The base includes a Traefik Ingress that connects the ClusterIP `mlflow`
Service to the cluster HTTP entrypoint. The manifest does not set a hostname.
The platform injects the hostname the same way it does for Risk API. A PVC
holds the server sqlite store and artifacts under `/mnt/course-mlflow`. The
object-count ResourceQuota already covers the extra Pod, Service, and PVC, so
this change does not raise the quota.

The server reuses `apps/model-trainer/Dockerfile`, the same image Compose uses
to run `mlflow server`. A digest-pinned GHCR image has not been published, so
the Deployment names `ghcr.io/seungbaeji/tta-aiqa-model-trainer` without an
OCI digest. Do not treat that image reference as a verified runtime.

Cluster publish and `/health` verification are pending. The configured context
`oracle/k3s` does not contain the course `tta-aiqa` namespace, so this
workstream did not apply or probe the tracking server. After the instructor
publishes the image by digest and the platform injects the Ingress host, set
`AIQA_MLFLOW_TRACKING_URI` and confirm:

```bash
curl "${AIQA_MLFLOW_TRACKING_URI%/}/health"
```

The leftover practice experiment is `practice-development-tracking`. The
server does not default the official experiment name
`tta-aiqa-physionet-2012-v2`.
