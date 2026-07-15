# Phase 0 Evidence

This directory contains reviewable evidence for the PhysioNet 2012 feasibility
gate. It is generated from versioned configuration and deterministic code.

```bash
uv run python -m scripts.phase0.main --stage all
```

- `f0-data-feasibility.json`: source integrity, join, target support, feature and
  split evidence.
- `f1-f2-model-feasibility.json`: repeated cross-validation, validation metrics,
  bootstrap intervals, selected profiles and gate decisions.
- `phase0-feasibility.md`: concise human-readable decision report.

The model evaluation reads only the `train` and `valid` roles. The final `test`
and `release_holdout` roles remain sealed until the later canonical benchmark.
Generated patient features and split rows are written under `artifacts/phase0/`
and are intentionally excluded from Git.
