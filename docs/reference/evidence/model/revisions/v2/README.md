# V2 Model Release Evidence

## 1. Lifecycle

### 1-1. Evidence order

The V2 evidence is intentionally read-only for students.

1. `model-bootstrap.json` records the train/valid bundles and MLflow model runs.
2. `release-freeze.json` records the pre-test evidence and bundle hashes.
3. `final-benchmark.json` records the sealed-test metrics.
4. `canonical-benchmark.json` records Candidate A `HOLD` and Candidate B
   `APPROVE`.
5. `release-manifest.json` is the post-test publication authorization.

## 2. Release Decision

### 2-1. Approved artifact

Candidate B is the only approved candidate. Its model and metadata SHA-256,
model MLflow run ID, final-evaluation MLflow run ID, canonical evidence digest,
and immutable publish path are bound by `release-manifest.json`.

Candidate A has no deployment overlay and cannot be published.

## 3. Historical Scope

### 3-1. Reconciliation boundary

V2 was migrated to add serialized model and metadata integrity checks after its
sealed test had already been evaluated. The original frozen DVC lock blob is
not available in this repository. The manifest records this explicitly in
`historical_reconciliation`; it verifies the sealed-test dataset digest,
canonical metrics, final benchmark, and serialized bundles without claiming a
new sealed-test evaluation or full source-lock reconstruction.

New revisions must use the normal Model Trainer lifecycle and produce a
complete freeze and manifest before their sealed test is opened.
