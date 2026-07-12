# Data Lineage Evidence

## 1. Scope

### 1-1. Historical evidence

`data-manifest.json` preserves the original V1 patient-level lineage.
`split-revision-v2.json` records the approved V2 role transition and dataset
digests. The exact DVC lock referenced by that data-lineage record is retained
at [`revisions/v2/frozen-dvc.lock`](revisions/v2/frozen-dvc.lock).

These files are review evidence. Student setup must read them but must not
overwrite them.

## 2. Reproduction

### 2-1. Current data workspace

```bash
uv run python scripts/prepare_data.py
uv run python scripts/validate_data.py
uv run dvc status
```

The commands reproduce ignored local data and runtime validation artifacts with
the active pipeline. The production `aiqa-data` output was compared cell by
cell with the Phase 0 feature artifact. The only split terminology change is
`release_holdout` to `operational`; patient assignments are unchanged.

## 3. Maintenance

### 3-1. New revision rule

The `build_*_evidence.py` scripts default to `artifacts/evidence-drafts/`.
Writing beneath `reference/evidence/` requires both an explicit output path and
`--write-historical-evidence`. Use them only while creating a new, explicitly
named revision. A data or pipeline change must produce new lineage and model
evidence rather than rewriting the V2 historical record.
