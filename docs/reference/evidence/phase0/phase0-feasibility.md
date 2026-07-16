# PhysioNet 2012 Phase 0 Feasibility

## Data Evidence

- Patient records: `4000`
- Measurement rows: `1757980`
- Deaths: `554`
- Death rate: `0.1385`
- Patient/outcome join failures: `0`
- Blocked outcome features present: `0`

## Gate Summary

- F0 data feasibility: `PASS`
- F1 predictive feasibility: `PASS`
- F2 scenario feasibility: `PASS`
- Overall: `GO`
- Model access roles: `train`, `valid` only
- Final `test` and `release_holdout`: not accessed

## Repeated Cross-Validation

| Profile | PR-AUC mean | PR-AUC std | AUROC mean | Recall mean |
| --- | ---: | ---: | ---: | ---: |
| dummy_prior | 0.139 | 0.001 | 0.500 | 0.000 |
| logistic_unweighted | 0.431 | 0.040 | 0.811 | 0.284 |
| logistic_balanced | 0.430 | 0.042 | 0.811 | 0.681 |
| random_forest_unweighted | 0.506 | 0.041 | 0.837 | 0.080 |
| random_forest_balanced | 0.489 | 0.041 | 0.835 | 0.381 |

## Missingness Shortcut Check

- Missing/count-only PR-AUC: `0.269` (std `0.022`)
- Full baseline PR-AUC: `0.431`
- Missingness carries signal but does not explain the full baseline signal.

## Validation Operating Points

| Role | Profile | Threshold | Precision | Recall | F1 | PR-AUC | TP | FP | FN | TN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | logistic_unweighted | 0.50 | 0.381 | 0.193 | 0.256 | 0.351 | 16 | 26 | 67 | 491 |
| Candidate A | random_forest_unweighted | 0.40 | 0.615 | 0.193 | 0.294 | 0.426 | 16 | 10 | 67 | 507 |
| Candidate B | random_forest_balanced | 0.35 | 0.339 | 0.783 | 0.473 | 0.412 | 65 | 127 | 18 | 390 |

## Bootstrap 95% Intervals

| Role | Precision | Recall | F1 | PR-AUC |
| --- | --- | --- | --- | --- |
| baseline | 0.250-0.533 | 0.114-0.282 | 0.163-0.361 | 0.264-0.466 |
| candidate_a | 0.421-0.800 | 0.114-0.280 | 0.182-0.397 | 0.333-0.545 |
| candidate_b | 0.272-0.408 | 0.692-0.867 | 0.398-0.547 | 0.324-0.526 |

## Decision

- Candidate A: `HOLD`
- Candidate B: `APPROVE`
- Baseline CV PR-AUC lift over Dummy: `0.2920`
- Candidate B approval criteria: all passed on validation evidence
- Conclusion: `GO` to the V2 implementation foundation; final model approval remains unconfirmed until the sealed test evaluation.

This is an education-only feasibility result, not evidence of clinical utility.
