# V2 Frozen Data Lineage

## 1. Purpose

### 1-1. Historical release input

`frozen-dvc.lock` is the exact DVC lock document referenced by
`reference/evidence/data-lineage/split-revision-v2.json`. It is immutable data
lineage evidence, not the active DVC lock file.

The historical V2 model freeze records a separate pre-migration lock digest
whose source blob is unavailable in this repository. The V2 release manifest
therefore records that limited verification scope rather than claiming that the
active lock reconstructs the sealed model release.

## 2. Active Reproduction

### 2-1. Student data workspace

Students run `uv run python scripts/prepare_data.py` against the active
`dvc.lock`. That command recreates local data and ignored runtime artifacts
with the current data-pipeline implementation. It must not rewrite historical
V2 evidence.

## 3. New Revisions

### 3-1. Evidence policy

A changed aggregation rule, split, source, or data-pipeline implementation
requires a new data and model revision. Do not replace this frozen lock or the
V2 sealed-test evidence to make a new run appear historical.
