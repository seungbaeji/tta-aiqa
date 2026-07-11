# Data Lineage Evidence

## 1. Scope

### 1-1. Purpose

`data-manifest.json` records the versioned source, configuration, DVC lock and generated patient-level dataset hashes used by V2. Full CSV outputs remain in the local DVC cache and are not committed to Git.

## 2. Reproduction

### 2-1. Commands

```bash
uv run python scripts/prepare_data.py
uv run python -m scripts.phase0.main --stage data
uv run python scripts/build_data_evidence.py
uv run dvc status
```

The production `aiqa-data` output was compared cell by cell with the Phase 0 feature artifact. The only split terminology change is `release_holdout` to `operational`; patient assignments are unchanged.
