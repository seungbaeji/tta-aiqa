# Data Quality Evidence

## 1. Scope

### 1-1. Validation suites

`ge-validation-summary.json` contains the reviewable result for two Great Expectations checkpoints.

- `raw-ingestion` validates patient record count, identifiers, observation support and the 48-hour timestamp boundary.
- `processed-readiness` validates the 4,000-row/133-feature schema, identifiers, target support and missing indicator contract.

Expected source missingness and sentinel observations are profile evidence, not reasons to reject the official dataset. Structural contract failures return a non-zero command status, but GE is not a DVC stage or dataset publish gate.

## 2. Reproduction

### 2-1. Commands

```bash
uv run aiqa-data-quality validate \
  --source-contract configs/contracts/physionet-record.yaml \
  --aggregation-config configs/data/aggregation.yaml \
  --split-config params.yaml \
  --patient-features data/processed/physionet-2012/patient-features.csv \
  --split-manifest data/splits/physionet-2012/split-manifest.csv \
  --source-evidence artifacts/data-quality/source-integrity.json \
  --quality-rules configs/data/quality-rules.yaml \
  --validation-artifact-dir artifacts/data-quality/great-expectations
uv run python scripts/build_quality_evidence.py
```

Generated Validation Results and Data Docs stay under `artifacts/data-quality/` and are excluded from Git.
