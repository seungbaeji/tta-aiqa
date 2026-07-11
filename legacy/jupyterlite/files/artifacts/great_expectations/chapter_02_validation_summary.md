# 2장 데이터 검증 요약

- 데이터셋: vital_signs_valid_degraded.csv
- 행(row) 수: 30003
- 전체 성공 여부: False
- 통과 기대 조건: 4
- 실패 기대 조건: 2

| 기대 조건(expectation) | 컬럼(column) | 성공 여부 | 실패 건수 | 실패 비율 | QA 사유 |
| --- | --- | --- | --- | --- | --- |
| `expect_column_to_exist` | `label` | True | 0 | 0.00% | 모델 평가 전 라벨(label) 컬럼이 필요합니다. |
| `expect_column_values_to_not_be_null` | `label` | True | 0 | 0.00% | 라벨(label) 결측은 지표(metric) 계산 신뢰도를 낮춥니다. |
| `expect_column_values_to_not_be_null` | `heart_rate` | False | 1501 | 5.00% | 모델 입력 특성(feature) 결측은 점수(score) 계산을 불안정하게 만들 수 있습니다. |
| `expect_column_values_to_be_in_set` | `label` | True | 0 | 0.00% | 허용된 이진 분류(binary classification) 라벨만 모델 평가에 사용해야 합니다. |
| `expect_column_values_to_be_between` | `oxygen_saturation` | False | 1201 | 4.00% | 허용 범위 밖 특성(feature)은 점수(score) 분포를 왜곡할 수 있습니다. |
| `expect_column_values_to_be_between` | `heart_rate` | True | 0 | 0.00% | 허용 범위 밖 특성(feature)은 점수(score) 분포를 왜곡할 수 있습니다. |
