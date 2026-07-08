# Label Basis Check

| source | target_column | allowed_labels | label_mapping | evaluation_ready |
| --- | --- | --- | --- | --- |
| data/release_regression_cases.csv | label | high_risk, low_risk | High Risk->high_risk, Low Risk->low_risk, high_risk->high_risk, low_risk->low_risk | True |

| label | count |
| --- | ---: |
| high_risk | 37 |
| low_risk | 33 |

| positive_label | positive_count | negative_label | negative_count | invalid_count | missing_count | positive_rate |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| high_risk | 37 | low_risk | 33 | 0 | 0 | 52.86% |
