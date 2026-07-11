# 2장 모델 품질 비교 리포트

이 리포트는 prepared artifact입니다. 직접 재생성하지 않았다면 `artifacts/reports/chapter_02_model_quality_comparison.md`에서 확인한 값이라고 보고서에 적습니다.

## 비교 조건

| 항목 | 값 |
| --- | --- |
| model_version | `v1` |
| model_path | `artifacts/models/chapter_02_baseline.pkl` |
| threshold | `0.50` |
| feature_columns | `heart_rate, respiratory_rate, body_temperature, oxygen_saturation, systolic_blood_pressure, diastolic_blood_pressure` |
| target_column | `label` |

## validation 기준/품질 저하 평가 데이터셋 지표 비교

| 데이터셋 | Accuracy | Precision | Recall | AUROC | PR-AUC | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| valid_baseline | 0.6995 | 1.0000 | 0.4281 | 0.7115 | 0.8003 | 0 | 9017 |
| valid_degraded | 0.6826 | 0.9828 | 0.4004 | 0.6962 | 0.7802 | 110 | 9413 |
| model_test | 0.7006 | 1.0000 | 0.4266 | 0.7185 | 0.8024 | 0 | 5989 |

## 변화량

| 항목 | 변화량 | QA 해석 |
| --- | --- | --- |
| Precision | -0.0172 | 정밀도 하락 여부 확인 |
| Recall | -0.0277 | 미탐 증가 여부 확인 |
| PR-AUC | -0.0201 | 관심 클래스 점수 구분력 약화 후보 확인 |
| FP | +110 | 오탐 증가로 운영 부담 증가 가능성 확인 |
| FN | +396 | 미탐 변화도 함께 확인 |

## 점수와 예측 분포

| 데이터셋 | score mean | score p10 | score p50 | score p90 | high_risk prediction | low_risk prediction |
| --- | --- | --- | --- | --- | --- | --- |
| valid_baseline | 0.5055 | 0.3669 | 0.3781 | 0.9556 | 6751 | 23252 |
| valid_degraded | 0.5002 | 0.3670 | 0.3782 | 0.9554 | 6396 | 23607 |

## QA 판단

같은 기준선 모델과 임계값 `0.50`에서 품질 저하 validation 데이터셋은 기준 validation 데이터셋보다 Precision이 1.0000에서 0.9828로 바뀌고, Recall은 0.4281에서 0.4004로 바뀌었습니다. FP는 0건에서 110건으로, FN은 9017건에서 9413건으로 바뀌었습니다. 따라서 입력 특성 품질 저하를 모델 지표 변화의 강한 원인 후보로 남깁니다.

다만 이 증거만으로 모델 자체 결함이나 배포 승인/보류를 확정하지 않습니다. 3장에서 API가 같은 `model_version`, feature 순서, threshold, 응답 필드를 사용하는지 확인해야 합니다.
