# ADR 0006: Layered Artifact Identity and Release Provenance

## 1. Status

### 1-1. Decision

Accepted on 2026-07-12.

## 2. Context

### 2-1. Problem

The course must explain why a particular data revision, model bundle, and deployed
service can be trusted without teaching an ad hoc list of Python-file checksums.
Hashes are useful at immutable artifact boundaries, but a manifest that enumerates
implementation files becomes brittle whenever a refactor moves code between modules.

The repository already uses DVC, MLflow, KServe, Kubernetes, Great Expectations,
OpenTelemetry, Grafana Alloy, and GitOps. Each tool has an established identity or
provenance surface. The course needs one clear responsibility for each surface.

### 2-2. Decision Drivers

- A student must be able to answer which data, model, and deployment is being viewed.
- A release decision must be reproducible without exposing sealed-test labels early.
- The design must work with a local DVC cache, local MLflow, PVC-backed model storage,
  and Grafana Cloud without requiring a paid registry or signing service.
- The material must distinguish an integrity record from a cryptographically signed
  supply-chain attestation.

## 3. Decision

### 3-1. Identity Ownership

| Boundary | Primary reference | Owner | Purpose |
| --- | --- | --- | --- |
| Source and versioned configuration | clean Git commit; `uv.lock` is part of that commit | Git | Identify the exact code and dependency definition. Do not list individual Python source hashes. |
| Raw, processed, and split data | DVC `dvc.lock`, source manifest, role dataset digest | DVC and data lineage evidence | Reproduce the pipeline and identify the exact sealed test file. |
| Trained model | MLflow run ID, logged model artifact, model artifact digest, feature-contract digest | MLflow and model bundle | Connect metrics and inputs to the serialized scoring artifact. |
| Release decision | generated `release-freeze.json` and `release-manifest.json` | Model Trainer and QA | Record what was frozen before test and what was approved after test. |
| Runtime deployment | OCI image digest, immutable model directory, expected model digest | GitOps and KServe Predictor | Identify the executable and reject a mounted model that is not the approved artifact. |

An identity is tool-owned whenever possible. A SHA-256 value is added when a binary
artifact crosses from one ownership boundary to another, such as model publication to
the course PVC or a container image publication to a registry.

### 3-2. Freeze Before Sealed Test

`release-freeze.json` is written only after train/valid bundle creation and before the
sealed test is opened. It records the Git commit, DVC/data-lineage reference, exact
test dataset digest, relevant configuration digests, MLflow run IDs, and both model and
external metadata digests for every candidate.

The final workflow verifies every frozen reference before it reads `test.csv` or loads a
bundle. The same workflow requires a clean worktree. A refactor therefore changes the
Git commit identity rather than requiring a new field for every moved module.

### 3-3. Release and Deployment

After a final evaluation, an approved candidate produces `release-manifest.json`. It
links the freeze manifest digest, canonical evidence digest, MLflow run ID, model
artifact digest, feature-contract digest, and approved profile. It is a generated,
reviewable release record, not a mutable configuration file.

GitOps deployment pins the predictor image as `image@sha256:<digest>` and selects a
content-addressed model directory on the course PVC. A non-secret ConfigMap supplies
the expected model digest to the predictor. The predictor compares it with the mounted
bundle before reporting readiness and returns the resolved model version through KServe
V2. A public Risk API never reloads a local file as a deployment mechanism; Argo CD and
KServe rollout own that change.

MLflow Tracking is required for the course. MLflow Model Registry version, tags, and an
alias are optional instructor-side release controls. A mutable alias is resolved to a
specific version when creating `release-manifest.json`; runtime deployment never relies
on a moving alias.

### 3-4. Educational Scope

Students trace one chain:

```text
Git commit + DVC data revision
  -> MLflow run and model artifact
  -> pre-test freeze
  -> canonical release decision
  -> immutable model publish and KServe version
  -> Risk API telemetry and Grafana Cloud dashboard
```

SLSA is used as a conceptual reference for provenance fields. The course does not claim
SLSA compliance unless a trusted builder and signed attestation are introduced later.

## 4. Alternatives Considered

### 4-1. Hash Every Source File in the Freeze Manifest

Rejected. It detects a local edit but couples provenance to the repository's module
layout. A refactor becomes an artificial release-input change and the list is easy to
forget. A clean Git commit is the source identity boundary.

### 4-2. Use Only a Git Commit

Rejected. A commit identifies source and versioned configuration, but not the exact
binary model, DVC output, container image, or external MLflow artifact consumed later.

### 4-3. Deploy a Mutable MLflow Alias Directly

Rejected for the course runtime. Registry aliases are useful release-control labels, but
they are intentionally mutable. The GitOps manifest must resolve an approved model to a
specific immutable artifact before deployment.

### 4-4. Implement Signed SLSA and OCI Artifact Signing Now

Deferred. It is valuable production supply-chain work, but it adds a trusted builder,
key management, registry policy, and verification workflow outside the current course
scope. The release manifest deliberately keeps a compatible provenance shape without
claiming that assurance level.

## 5. Consequences

### 5-1. Positive

- Each course tool explains one part of the lineage rather than duplicating another
  tool's job.
- Students see a concise reason for every identifier: Git for source, DVC for data,
  MLflow for experiment/model, and digests for published artifacts.
- The pre-test freeze and runtime readiness checks are testable contracts.
- Grafana evidence can be tied to a model version that was actually approved.

### 5-2. Cost

- The Model Trainer must generate and verify two explicit documents: a pre-test freeze
  and a post-decision release manifest.
- The publish and KServe paths need expected-digest settings and mismatch tests.
- Release automation must reject a dirty worktree and an unresolved image tag.

## 6. References

### 6-1. Official Tool References

- [DVC command reference](https://dvc.org/doc/command-reference/): DVC pipeline and
  lock-file workflow for data artifacts.
- [MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/): model
  versions, lineage, tags, aliases, and model URIs.
- [MLflow Models](https://mlflow.org/docs/latest/ml/model/index.html): packaged model,
  signature, input example, and dependency metadata.
- [Kubernetes images](https://kubernetes.io/docs/concepts/containers/images/): an image
  digest identifies immutable image content.
- [KServe V2 protocol](https://kserve.github.io/website/docs/concepts/architecture/data-plane/v2-protocol):
  standard inference, health, metadata, and model-version surfaces.
- [SLSA provenance v1](https://slsa.dev/spec/v1.0/provenance): artifact digests and
  resolved build dependencies in a provenance record.
- [Great Expectations Checkpoints and Actions](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions/):
  validation results can drive documentation, notification, or a policy action.
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) and
  [Grafana Alloy OTLP setup](https://grafana.com/docs/opentelemetry/collector/grafana-alloy/):
  application signals and collector delivery.
- [Grafana dashboard import](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/import-dashboards/)
  and [data source API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/):
  stable dashboard UIDs and datasource UID/type lookup.
- [Grafana k6 scenarios](https://grafana.com/docs/k6/latest/using-k6/scenarios/):
  workload modeling kept separate from domain-specific traffic simulation.
