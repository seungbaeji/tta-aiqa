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
[`runtime-images-v2-20260908-23fbb5d.json`](../../docs/evidence/deployment/runtime-images-v2-20260908-23fbb5d.json).
The deployment contract test rejects manifests that drift from this record or
runtime build inputs that changed after the recorded source commit.

Candidate B and rollback are Kustomize overlays. Students inspect rendered
manifests, then connect the course git repository and sync from the shared
Argo CD UI with the `tta` account. The instructor still provisions `ghcr-pull`.

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

After an overlay is synchronized, verify that stage without applying or
patching any resource. Students sync Candidate B from the shared Argo UI or
`scripts/platform/sync_student_release.py`; rollback Demo stays with the
instructor. Use `baseline-observed` when the baseline stage must emit live
telemetry, then synchronize `candidate-b` and `rollback`.
Run the verifier with release names `baseline`, `candidate-b`, and `rollback`,
using a different output file each time.

```bash
uv run python scripts/platform/verify_target_release.py \
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

Closed-network learners reach Compose `mlflow` through the platform HTTPS URL
and set `AIQA_MLFLOW_TRACKING_URI` to that URL. They do not create a ClusterIP
Service, port-forward, or tunnel, and they do not use
`http://127.0.0.1:5000` as the recorded classroom path.

Compose publishes `0.0.0.0:5000` and passes `--allowed-hosts *` with
`--cors-allowed-origins *`. Host allowlist alone still blocks browser POST
from the public HTTPS origin, and the UI shows that 403 as a permission
error. Kubernetes
manifests for a tracking server stay in `deploy/k8s/base/` as
`mlflow.yaml`, `mlflow-ingress.yaml`, and `mlflow-pvc.yaml`. They are not
listed in `kustomization.yaml` resources, so course overlays do not apply
them. Do not add them next to the Risk API Ingress.

```bash
curl "${AIQA_MLFLOW_TRACKING_URI%/}/health"
```

The student development experiment is `student-development-tracking`. The
server does not default the official experiment name
`tta-aiqa-physionet-2012-v2`. Students log that run from
`labs/chapters/ch02/03_log_student_mlp.ipynb`.
