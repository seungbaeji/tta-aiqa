# 2장 모델 품질 Lab

2장은 모델 성능 숫자를 계산하는 데서 끝나지 않고, 같은 모델과 같은 threshold에서 데이터 조건 변화가 어떤 metric, confusion matrix, score 분포, prediction 분포 변화로 이어지는지 QA 관점으로 설명하는 실습입니다.

## 실습 자료

| 구분 | 경로 | 역할 |
| --- | --- | --- |
| README | `labs/ch02_model_quality/README.md` | 2장 실습 목적, 실행 순서, 예상 출력, QA 해석 |
| Great Expectations API 기초 Notebook | `labs/ch02_model_quality/05_great_expectations_api_basics_lab.ipynb` | 작은 예제로 GE API 기본 흐름 확인 |
| Great Expectations Notebook | `labs/ch02_model_quality/06_great_expectations_lab.ipynb` | validation 품질 검증 artifact 재생성 |
| 초급 Notebook 1 | `labs/ch02_model_quality/01_score_threshold.ipynb` | score, threshold, prediction 관계 확인 |
| 초급 Notebook 2 | `labs/ch02_model_quality/02_train_evaluate_track_lab.ipynb` | 후보 모델을 반복 학습하고 run별 평가/기록 table 생성 |
| 초급 Notebook 3 | `labs/ch02_model_quality/03_precision_recall.ipynb` | Confusion Matrix, Precision, Recall, FP/FN 해석 |
| 초급 Notebook 4 | `labs/ch02_model_quality/04_read_metric_record.ipynb` | 모델 버전, 데이터셋, threshold, metric 기록 확인 |
| 참고 모델 평가 Notebook | `labs/ch02_model_quality/07_model_evaluation_lab.ipynb` | 전체 모델 평가 흐름을 한 번에 다시 볼 때 사용 |
| 참고 데이터-지표 연결 Notebook | `labs/ch02_model_quality/08_data_metric_connection_lab.ipynb` | 전체 데이터 품질 신호와 metric 변화 연결을 다시 볼 때 사용 |
| MLflow Notebook | `labs/ch02_model_quality/09_mlflow_tracking_lab.ipynb` | 평가 기록과 재현 범위 확인 |
| 학습 script | `labs/ch02_model_quality/10_train_baseline.py` | 기준선 모델 artifact 생성 |
| 평가 기록 script | `labs/ch02_model_quality/11_evaluate_and_record.py` | test metric과 experiment 기록 생성 |
| 비교 artifact script | `labs/ch02_model_quality/12_build_comparison_artifacts.py` | validation degradation 비교 JSON/Markdown 생성 |

## 직접 실행 순서

2장 CLI 재생성은 다음 세 script를 순서대로 실행합니다.

```bash
uv run python labs/ch02_model_quality/10_train_baseline.py
uv run python labs/ch02_model_quality/11_evaluate_and_record.py
uv run python labs/ch02_model_quality/12_build_comparison_artifacts.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-model-quality
```


## 2-4. 모델 성능 평가 실습

모델 성능 평가 Lab의 목표는 같은 모델을 같은 기준으로 평가하고 지표(metric)를 QA 관점에서 읽는 것입니다. 2-2에서 확인한 품질 저하 validation 데이터셋의 검증 실패가 실제 지표, 혼동 행렬(Confusion Matrix), 임계값(threshold) 비교에서 어떤 판단 근거로 이어지는지 확인합니다.

이 Lab의 `vital_signs_valid_degraded.csv`는 현재 운영 입력 샘플에서 나타날 수 있는 결측, 범위 오류, 일부 라벨 기준 흔들림을 validation 기준에서 교육용으로 재현한 비교 데이터입니다. 실제 운영 입력 샘플은 4장과 5장에서 운영 holdout 로그와 대시보드 증거로 다시 확인하고, 2장에서는 같은 조건에서 평가 가능한 비교 artifact로 지표 변화를 읽습니다.

이 Lab에서 수강생은 모델을 튜닝하는 사람이 아니라, 평가 결과를 검토하는 품질/운영 담당자 역할을 맡습니다. **핵심 질문은 “성능이 몇 점인가”가 아니라 “같은 모델과 같은 임계값에서 데이터 조건이 달라졌을 때 어떤 오류 유형이 늘었고, 어떤 제한 사항을 QA 코멘트에 남겨야 하는가”입니다.**

이 Lab의 핵심은 scikit-learn 평가 출력과 평가 조건 기록을 같은 QA 판단 흐름으로 묶는 것입니다. 문서는 각 출력의 의미와 QA 해석을 설명하고, Notebook은 같은 흐름을 셀 단위로 실행하는 산출물입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch02_model_quality/README.md` | 실습 목적, 예상 출력, QA 해석 확인 |
| 초급 Notebook | `labs/ch02_model_quality/01_score_threshold.ipynb`, `02_train_evaluate_track_lab.ipynb`, `03_precision_recall.ipynb`, `04_read_metric_record.ipynb` | score/prediction, 반복 학습 기록, 오류 유형, metric 기록을 나누어 확인 |
| 참고 Notebook | `labs/ch02_model_quality/07_model_evaluation_lab.ipynb` | 전체 모델 평가 흐름을 한 번에 다시 볼 때 사용 |
| CLI 학습 스크립트 | `labs/ch02_model_quality/10_train_baseline.py` | 기준선 모델 artifact 생성 |
| 평가 기록 | `artifacts/experiments/chapter_02/model_test_eval.json` | 선택된 모델과 threshold의 test metric 확인 |
| 비교 기록 | `artifacts/experiments/chapter_02/validation_degradation_comparison.json` | validation 기준/품질 저하 평가 지표, 점수 분포, 예측 분포, 임계값 비교 확인 |
| 보고서용 비교 리포트 | `artifacts/reports/chapter_02_model_quality_comparison.md` | 릴리스 판단 보고서에 인용할 비교표와 QA 판단 확인 |

실습 흐름은 train split으로 기준선을 만든 뒤, validation split에서 threshold 후보와 품질 저하 비교를 확인하고, 마지막에 test split으로 선택된 모델과 threshold를 평가하는 순서입니다. 이 순서를 지켜야 모델 변경, 데이터 조건 변화, 운영 기준 변경을 서로 섞지 않고 해석할 수 있습니다.

준비된 artifact가 있는 환경에서는 먼저 `model_test_eval.json`과 `validation_degradation_comparison.json`을 확인합니다. `02_train_evaluate_track_lab.ipynb`는 notebook 안에서 여러 후보를 실제로 `fit()`해 보고 run table을 만드는 초급 예제입니다. 전체 데이터 기준의 canonical artifact는 `10_train_baseline.py`, `11_evaluate_and_record.py`, `12_build_comparison_artifacts.py`, `uv run python scripts/course.py lab-model-quality`로 다시 만듭니다. 직접 실행하지 않았다면 보고서에는 “prepared artifact에서 확인한 값”이라고 적습니다.

## 2-4-1. scikit-learn 기반 트리 분류 모델 학습

실습 목표는 같은 데이터와 특성(feature)으로 재현 가능한 기준선을 만드는 것입니다. 기준선은 이후 품질 저하 validation 데이터셋, 임계값 변경, 모델 버전 비교의 기준점입니다. 여기서 기준선은 “승인 가능한 모델”이라는 뜻이 아니라, 이후 비교에서 흔들리지 않게 고정해 둘 출발 모델입니다.

이 단계의 준비 데이터와 특성 정의는 이후 평가 조건을 재현하기 위한 기준입니다. 준비 데이터는 `data/vital_signs_train.csv`입니다. 특성 정의는 `configs/validation/model_features.yaml`을 사용하고, 모델 저장 위치는 `artifacts/models/chapter_02_baseline.pkl`입니다. 모델 학습 코드는 `packages/ai-quality/src/ai_quality/model_quality/infrastructure/sklearn_classifier.py`에 있으며, 이 과정에서는 `RandomForestClassifier` 기반 기준선 모델을 사용합니다.

이 실행은 이후 validation 비교와 test 평가에 사용할 기준선 모델 artifact를 생성합니다. 실행 환경은 저장소 루트의 로컬 shell이며, 실행 코드는 다음과 같습니다.

```bash
uv run python labs/ch02_model_quality/10_train_baseline.py
```

이 출력에서 확인할 핵심은 학습 행 수, 특성 목록, 모델 저장 경로가 평가 기록에 남길 조건과 일치하는지입니다. 예상 결과는 baseline 모델 파일과 학습 요약 출력입니다.

```text
trained_rows=110011
features=['heart_rate', 'respiratory_rate', 'body_temperature', 'oxygen_saturation', 'systolic_blood_pressure', 'diastolic_blood_pressure']
model_path=/.../artifacts/models/chapter_02_baseline.pkl
```

수강생은 모델 구조나 하이퍼파라미터를 깊게 수정하지 않습니다. 대신 어떤 데이터셋(dataset), 어떤 특성 목록, 어떤 라벨(label) 기준으로 기준선이 만들어졌는지 확인합니다.

**QA 해석에서 중요한 것은 기준선이 비교 기준이라는 점입니다.** 이후 지표가 좋아졌거나 나빠졌다고 말하려면 먼저 기준 모델이 있어야 합니다. 기준선 없이 새 모델 하나만 평가하면 품질 회귀를 판단하기 어렵습니다.

이 단계에서 QA가 남길 기록은 모델 파일 자체보다 비교 조건입니다. 어떤 데이터셋, 어떤 특성, 어떤 라벨, 어떤 모델 artifact로 이후 지표를 계산했는지 적어야 2-4-3과 2-6에서 결과를 다시 비교할 수 있습니다.

실패 시 확인 포인트는 다음과 같습니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 데이터 파일을 찾지 못함 | `data` 경로와 `labs/prepare_data.py` 실행 여부를 확인 |
| 특성 컬럼 오류 | `configs/validation/model_features.yaml`과 데이터 컬럼을 비교 |
| 라벨 오류 | `low_risk`, `high_risk` 외 값이 있는지 확인 |
| 모델 저장 실패 | `artifacts/models` 디렉터리 생성 여부를 확인 |

## 2-4-2. test 데이터셋 기반 최종 모델 평가

실습 목표는 학습과 validation에 사용하지 않은 test 데이터셋에서 선택된 모델과 threshold의 지표를 계산하고, 정확도(Accuracy)만이 아니라 정밀도(Precision), 재현율(Recall), 혼동 행렬을 함께 해석하는 것입니다.

이 단계의 준비 데이터와 모델은 선택된 조건을 test 기준으로 검증하기 위한 것입니다. 준비 데이터는 `data/vital_signs_test.csv`이고, 준비 모델은 2-4-1에서 생성한 기준선 모델입니다. 임계값은 validation에서 비교한 후보 중 운영 기준으로 고정한 기본값 `0.50`을 사용합니다. `vital_signs_train.csv`는 기준선 학습에 사용하고, `vital_signs_test.csv`는 선택 이후 최종 모델 평가에만 사용합니다.

이 실행은 같은 scikit-learn 모델의 test metric과 평가 조건을 하나의 기록으로 남깁니다. 강의 중에는 `labs/ch02_model_quality/03_precision_recall.ipynb`와 `04_read_metric_record.ipynb`에서 준비된 평가 기록을 읽습니다. 명령행에서는 먼저 2-4-1의 `10_train_baseline.py`로 기준선 모델을 만들고, 이어서 `11_evaluate_and_record.py`로 `artifacts/experiments/chapter_02/model_test_eval.json`에 기록합니다.

```bash
uv run python labs/ch02_model_quality/11_evaluate_and_record.py
```

이 출력에서 확인할 핵심은 FP/FN과 주요 metric이 같은 데이터셋, 같은 threshold 조건에서 계산되었는지입니다. 예상 출력은 다음과 같은 형식입니다.

```text
dataset=vital_signs_test
threshold=0.50
row_count=20002
confusion_matrix=TP:4455 FP:0 FN:5989 TN:9558
metrics=accuracy:0.7006 precision:1.0000 recall:0.4266 f1:0.5980 auroc:0.7200 pr_auc:0.8033
```

**QA 해석에서는 먼저 혼동 행렬을 봅니다.** TP(True Positive)와 TN(True Negative)은 맞힌 샘플(sample)이고, FP(False Positive)와 FN(False Negative)은 오류입니다. 정밀도는 FP의 영향을 받고, 재현율은 FN의 영향을 받습니다. 따라서 정확도 `0.7006`이라는 숫자만 보고 끝내면 안 됩니다.

이 결과를 다음처럼 읽을 수 있습니다.

| 항목 | 값 | 해석 |
| --- | --- | --- |
| TP | 4455 | 관심 클래스(Positive class)를 맞게 탐지한 수 |
| FP | 0 | 비교 클래스(Negative class) 샘플을 관심 클래스로 잘못 예측한 오탐 |
| FN | 5989 | 관심 클래스 샘플을 놓친 미탐 |
| 정확도 | 0.7006 | 전체 샘플 중 맞힌 비율 |
| 정밀도 | 1.0000 | 관심 클래스로 예측한 것 중 실제 관심 클래스 비율 |
| 재현율 | 0.4266 | 실제 관심 클래스 중 탐지한 비율 |
| PR-AUC(AUPRC) | 0.8033 | 임계값 하나에 묶이지 않은 관심 클래스 탐지 품질 참고 |

실패 시 확인 포인트는 모델 파일 존재 여부, 특성 컬럼 일치 여부, 임계값 설정값입니다. 평가 코드가 실행되더라도 라벨 기준이 잘못되면 지표 해석이 틀릴 수 있으므로 허용 라벨 목록도 함께 확인합니다.

## 2-4-3. 기준 데이터셋과 품질 저하 데이터셋 비교

실습 목표는 데이터 품질 저하가 지표에 어떤 영향을 주는지 확인하는 것입니다. `vital_signs_valid_degraded.csv`는 현재 운영 입력 샘플의 실패 양상을 교육용으로 재현하기 위해 2-2에서 확인한 결측값(missing value), 범위 오류, 일부 라벨 반전(label flip)을 포함합니다. 라벨 반전은 값은 `high_risk` 또는 `low_risk`처럼 허용 목록 안에 있지만, 정답 기준이 일부 반대로 들어간 상태를 뜻합니다.

이 비교에서 라벨 관련 판단은 두 층으로 나누어야 합니다. 허용 라벨 검증은 지표 계산 형식이 가능한지 확인하고, 라벨 반전 후보는 지표가 실제 품질을 얼마나 믿을 수 있게 반영하는지 확인합니다.

| 구분 | 확인 질문 | 이번 Lab에서의 의미 | 보고서 표현 |
| --- | --- | --- | --- |
| 허용 라벨 검증 | 값이 `high_risk`, `low_risk` 안에 있는가 | 지표 계산 형식은 유지됨 | “허용 라벨 기준은 통과했습니다.” |
| 정답 기준 신뢰 | 일부 행의 정답이 반대로 들어갔을 가능성이 있는가 | FP/FN과 지표 변화를 직접 흔들 수 있음 | “라벨 반전 후보는 별도 제한 사항으로 남깁니다.” |
| 입력 특성 품질 | 결측과 범위 오류가 점수에 영향을 주는가 | 점수와 예측 분포 변화의 원인 후보 | “입력 특성 품질 이슈와 라벨 기준 후보를 분리해 확인합니다.” |

이 단계의 준비 데이터는 같은 모델에서 데이터 조건 변화의 영향을 분리하기 위한 비교 기준입니다. 준비 데이터는 기준 validation 데이터셋과 품질 저하 validation 데이터셋입니다. 같은 모델을 두 데이터셋에 적용해 지표 변화를 비교합니다. 모델이 같기 때문에 지표 변화의 주요 원인 후보는 데이터 차이에서 찾을 수 있습니다.

이 비교는 실행 여부와 관계없이 같은 artifact 값을 기준으로 QA 해석을 만들 수 있어야 합니다. 강의 중에는 `labs/ch02_model_quality/03_precision_recall.ipynb`와 `04_read_metric_record.ipynb`에서 핵심 값만 확인합니다. 읽기 전용으로 확인할 때는 `artifacts/experiments/chapter_02/validation_degradation_comparison.json`과 `artifacts/reports/chapter_02_model_quality_comparison.md`를 열어 같은 값을 확인합니다.

prepared artifact에서 확인할 기준 validation 데이터셋과 품질 저하 validation 데이터셋의 지표 비교는 다음과 같습니다.

| 데이터셋 | 정확도 | 정밀도 | 재현율 | AUROC | PR-AUC | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| valid_baseline | 0.6995 | 1.0000 | 0.4281 | 0.7116 | 0.7999 | 0 | 9017 |
| valid_degraded | 0.6826 | 0.9828 | 0.4004 | 0.6965 | 0.7806 | 110 | 9413 |
| model_test | 0.7006 | 1.0000 | 0.4266 | 0.7200 | 0.8033 | 0 | 5989 |

`validation_degradation_comparison.json`의 delta 값에서는 정확도가 `-0.0169`, 정밀도가 `-0.0172`, 재현율이 `-0.0277`, F1이 `-0.0306`, FP 변화가 `+110`, FN 변화가 `+396`로 나타납니다. **수강생은 어떤 지표가 변했는지, FP/FN 중 무엇이 더 크게 변했는지 확인해야 합니다.**

QA 해석에서는 “지표가 낮아졌다”에서 멈추지 않습니다. 결측값 때문에 점수(score)가 불안정해졌는지, 범위 오류가 점수 분포를 왜곡했는지, 라벨 반전이 지표를 직접 흔들었는지 원인 후보를 분리해야 합니다.

| 관측 결과 | 2-2에서 연결할 품질 신호 | 가능한 원인 후보 | 다음 확인 |
| --- | --- | --- | --- |
| FP 증가 | `oxygen_saturation` 범위 오류 | 점수 분포 이동, 입력 특성 왜곡 | 점수 분위수와 예측(prediction) 분포 확인 |
| 정밀도 하락 | FP 증가와 연결 | 관심 클래스 예측 안에 실제 `low_risk`가 더 많이 포함 | FP가 발생한 행(row)의 입력 특성 확인 |
| AUROC/PR-AUC 하락 | 결측값과 범위 오류 | 임계값 하나가 아니라 점수 구분력 약화 | 기준/품질 저하 데이터셋의 점수 분포 비교 |
| 재현율 하락 | FN 증가와 연결 | 실제 관심 클래스 샘플을 더 많이 놓침 | threshold와 품질 저하 행을 함께 확인 |

**이번 출력에서는 품질 저하 validation 데이터셋에서 FP가 `0`에서 `110`로 증가하고 정밀도가 낮아졌습니다.** 따라서 QA 코멘트에는 오탐(FP)과 미탐(FN) 증가, 점수 분포 확인 필요, 입력 품질 원인 후보를 함께 남깁니다. 다음 단계에서는 이 원인 후보를 점수 분포와 예측 분포로 더 좁혀 봅니다.

실패 시 확인 포인트는 품질 저하 validation 데이터셋 경로, 라벨 값, 결측값 처리 방식입니다. 특히 품질 저하 validation 데이터셋에 허용되지 않은 라벨이 포함되어 있으면 평가 전에 데이터 검증 결과를 먼저 확인해야 합니다.

## 2-4-4. 임계값 변화에 따른 정밀도/재현율 비교

실습 목표는 임계값이 정밀도와 재현율에 미치는 영향을 직접 확인하는 것입니다. 같은 모델과 같은 점수를 사용하더라도 임계값이 달라지면 예측이 달라지고, FP/FN이 달라집니다.

이 단계의 준비 데이터는 기준선 평가와 동일해야 임계값 변경 효과만 분리할 수 있습니다. 준비 데이터는 기준선 평가와 동일합니다. 중요한 것은 모델을 다시 학습하지 않고 임계값만 바꾼다는 점입니다. 이렇게 해야 임계값 변경의 영향만 분리해서 볼 수 있습니다.

이 실행에서 확인할 핵심은 같은 점수에 임계값만 바꿔 적용했는지입니다. Notebook에서는 `labs/ch02_model_quality/01_score_threshold.ipynb`에서 score, threshold, prediction의 관계를 먼저 확인합니다. 모델을 다시 학습하지 않고 같은 점수에 임계값만 바꿔 적용했는지 확인합니다.

이 결과에서 확인할 핵심은 임계값이 오류 유형의 균형을 어떻게 바꾸는지입니다. 예상 결과는 임계값별 정밀도, 재현율, FP, FN 비교입니다.

| 임계값 | 정밀도 | 재현율 | FP | FN | QA 해석 |
| --- | --- | --- | --- | --- | --- |
| 0.30 | 0.5221 | 1.0000 | 9558 | 0 | 모든 관심 클래스를 탐지하지만 오탐이 큼 |
| 0.50 | 1.0000 | 0.4266 | 0 | 5989 | 운영 기준 비교점 |
| 0.70 | 1.0000 | 0.4266 | 0 | 5989 | 현재 점수 분포에서는 0.50과 같은 예측 결과 |

**QA 해석에서는 임계값을 모델 지표를 자동으로 개선하는 설정으로 보면 안 됩니다.** 임계값은 오류 유형의 균형을 바꾸는 운영 기준입니다. 어떤 임계값이 적절한지는 서비스에서 FP와 FN 중 어떤 오류가 더 부담이 큰지에 따라 달라집니다.

실패 시 확인 포인트는 점수 범위, 임계값, 라벨 기준입니다. 점수가 `0`에서 `1` 범위가 아니거나 임계값 설정이 잘못되면 결과 해석이 달라집니다. 또한 임계값 분석 결과를 보고할 때는 정밀도/재현율만이 아니라 FP/FN 개수도 함께 제시해야 합니다.

## 2-4-5. 혼동 행렬 표 해석

실습 목표는 혼동 행렬을 숫자로 읽고, FP와 FN이 품질 판단에 어떤 의미를 갖는지 설명하는 것입니다. 2-4-5는 새로운 스크립트를 실행하는 단계가 아니라, 2-4-2와 2-4-4에서 이미 나온 출력을 품질 판단 문장으로 바꾸는 해석 단계입니다.

준비 데이터와 모델은 기준선 평가와 동일합니다. 강의 자료에서는 혼동 행렬을 표로 보여주고, 수강생은 TP, FP, FN, TN이 각각 어떤 의미인지 설명합니다.

실행 결과는 2-4-2 평가 스크립트의 `confusion_matrix` 출력을 사용합니다. 중요한 것은 그림을 예쁘게 만드는 것이 아니라, 표의 각 칸이 운영 품질에 어떤 의미인지 이해하는 것입니다.

이 구조에서 확인할 핵심은 실제 라벨과 예측 라벨의 조합이 어떤 오류 유형을 만드는지입니다. 예상 결과는 다음과 같은 구조입니다.

|  | 예측 `high_risk` | 예측 `low_risk` |
| --- | --- | --- |
| 실제 `high_risk` | TP | FN |
| 실제 `low_risk` | FP | TN |

**QA 해석에서는 FP와 FN을 따로 설명해야 합니다.** FP가 늘어난 모델과 FN이 늘어난 모델은 같은 정확도를 가질 수 있어도 운영 의미가 다릅니다. 이 차이를 설명하지 못하면 AI QA 보고서가 단순 지표 나열에 머물게 됩니다.

2-4의 최종 코멘트는 다음 형태로 정리할 수 있습니다.

```text
같은 기준선 모델과 임계값 0.50에서 품질 저하 validation 데이터셋을 비교한 결과,
정밀도는 낮아지고 FP는 증가했습니다.
2-2 검증 리포트에서 확인한 `heart_rate` 결측과 `oxygen_saturation` 범위 오류를
지표 변화의 원인 후보로 남기고, 점수 분포와 예측 분포를 확인합니다.
```

실패 시 확인 포인트는 라벨 순서입니다. 혼동 행렬을 그릴 때 관심 클래스와 비교 클래스 축이 바뀌면 FP와 FN 해석이 반대로 될 수 있습니다. 반드시 관심 클래스가 `high_risk`인지 확인하고 표를 읽어야 합니다.

## 2-5. 데이터 품질과 성능 지표의 연결

2-5 Lab의 목표는 데이터 품질 저하와 모델 지표(metric) 변화를 하나의 QA 설명으로 연결하는 것입니다. 2-4에서 같은 모델을 기준 validation 데이터셋과 품질 저하 validation 데이터셋에 적용했다면, 2-5에서는 그 결과를 점수(score) 분포, 예측(prediction) 분포, FP/FN 변화와 연결해 원인 후보를 정리합니다.

여기서 `vital_signs_valid_degraded.csv`는 현재 운영 입력 샘플의 실패 양상을 validation 기준에서 교육용으로 재현한 비교 artifact입니다. 따라서 2-5의 목적은 “degraded 파일이 실제 운영 데이터다”라고 주장하는 것이 아니라, 운영 입력 변화가 생겼을 때 같은 모델과 같은 threshold에서 어떤 지표와 분포를 함께 봐야 하는지 연습하는 것입니다.

이 Lab의 핵심은 데이터 품질 신호와 지표 변화를 같은 원인 후보 설명으로 묶는 것입니다. 문서는 관측값을 어떻게 읽을지 설명하고, Notebook은 같은 흐름을 셀 단위로 실행합니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch02_model_quality/README.md` | 데이터 품질 신호와 지표 변화 해석 |
| 초급 Notebook | `labs/ch02_model_quality/03_precision_recall.ipynb`, `04_read_metric_record.ipynb` | 기준 데이터셋과 품질 저하 데이터셋의 오류 유형과 metric 기록 확인 |
| 참고 Notebook | `labs/ch02_model_quality/08_data_metric_connection_lab.ipynb` | 전체 데이터-지표 연결 흐름을 한 번에 다시 볼 때 사용 |
| 비교 JSON artifact | `artifacts/experiments/chapter_02/validation_degradation_comparison.json` | validation 기준/품질 저하 평가 metrics, delta, score/prediction distribution, threshold analysis 확인 |
| 보고서용 비교 리포트 | `artifacts/reports/chapter_02_model_quality_comparison.md` | 릴리스 회의 보고서에 인용할 비교표와 QA 판단 확인 |
| CLI 재실행 경로 | `uv run python scripts/course.py lab-model-quality` | 기준선 모델과 2장 비교 산출물 재생성 |

Notebook으로 실습한다면 `labs/ch02_model_quality/03_precision_recall.ipynb`를 먼저 열고, 이어서 `labs/ch02_model_quality/04_read_metric_record.ipynb`를 실행합니다. 명령행에서는 `uv run python scripts/course.py lab-model-quality`로 2-4-1 기준선 모델과 2장 비교 산출물을 다시 만들 수 있습니다. 읽기 전용 리허설에서는 `validation_degradation_comparison.json`과 보고서용 Markdown을 열어 기준 validation 데이터셋과 품질 저하 validation 데이터셋의 지표, 점수 분위수, 예측 분포를 확인합니다.

## 2-5-1. 기준 데이터셋과 품질 저하 데이터셋 비교

실습 목표는 2-4에서 확인한 지표 변화를 출발 관측값으로 고정하는 것입니다. 기준 데이터는 `vital_signs_valid_baseline.csv`이고, 품질 저하 비교용 데이터는 `vital_signs_valid_degraded.csv`입니다. 이 비교용 데이터는 현재 운영 입력 샘플에서 나타날 수 있는 결측과 범위 오류를 validation 기준에서 재현한 교육용 데이터입니다.

**이 비교에서 중요한 전제는 모델과 임계값(threshold)을 고정한다는 점입니다.** 모델 버전이나 임계값이 함께 바뀌면 지표 변화의 원인을 데이터 품질로 보기 어렵습니다. 2-5는 데이터 조건 변화에 집중하므로 2-4에서 만든 기준선 모델과 운영 임계값 `0.50`을 그대로 사용합니다.

이 실행에서 확인할 핵심은 같은 모델과 threshold에서 데이터 조건 변화만 비교했는지입니다. Notebook에서는 `labs/ch02_model_quality/03_precision_recall.ipynb`의 지표 비교 셀과 `04_read_metric_record.ipynb`의 조건 확인 셀을 실행합니다. 명령행에서 전체 Lab 산출물을 다시 만들 때는 `uv run python scripts/course.py lab-model-quality`를 사용합니다. 이미 준비된 artifact가 있다면 `artifacts/reports/chapter_02_model_quality_comparison.md`에서 같은 비교표를 먼저 확인합니다.

prepared artifact에서 확인할 핵심 값은 다음과 같습니다.

| 데이터셋 | 정확도(Accuracy) | 정밀도(Precision) | 재현율(Recall) | AUROC | PR-AUC(AUPRC) | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 기준 validation | 0.6995 | 1.0000 | 0.4281 | 0.7116 | 0.7999 | 0 | 9017 |
| 품질 저하 validation | 0.6826 | 0.9828 | 0.4004 | 0.6965 | 0.7806 | 110 | 9413 |

**이 결과에서는 품질 저하 validation 데이터셋에서 정확도, 정밀도, AUROC, PR-AUC가 낮아지고 FP가 `0`건에서 `110`건으로 증가합니다.** 재현율도 낮아졌으므로 개선으로 볼 수 없습니다. 같은 임계값에서 `high_risk` 예측 수는 줄었지만, 그 안에 FP가 새로 생기고 FN도 증가했기 때문에 오류 유형을 함께 확인해야 합니다.

QA 해석에서는 “지표가 낮아졌다”가 아니라 “같은 모델과 임계값에서 품질 저하 validation 데이터셋의 FP와 FN이 증가하고, 정밀도, 재현율, PR-AUC가 낮아졌다”처럼 조건과 변화 방향을 함께 적습니다. 2-5의 다음 단계는 이 관측값을 점수와 예측 분포로 설명할 수 있는지 확인하는 것입니다.

## 2-5-2. 점수와 예측 분포 확인

실습 목표는 지표 변화가 예측 분포와 어떻게 연결되는지 확인하는 것입니다. 지표는 라벨(label)과 예측을 비교한 결과이고, 예측은 점수에 임계값을 적용한 결과입니다. 따라서 지표가 달라졌다면 점수와 예측 분포를 함께 봐야 합니다.

점수와 예측 분포는 지표 변화가 임계값 근처 샘플 이동과 연결되는지 확인하는 증거입니다. Notebook에서는 같은 모델로 기준 validation 데이터셋과 품질 저하 validation 데이터셋의 점수를 만들고, 운영 임계값 `0.50`을 적용해 예측을 계산합니다. 읽기 전용으로 확인할 때는 `validation_degradation_comparison.json`의 `score_distribution`을 봅니다. 요약은 다음과 같습니다.

| 데이터셋 | 점수 평균 | 점수 p10 | 점수 p50 | 점수 p90 | `high_risk` 예측 | `low_risk` 예측 |
| --- | --- | --- | --- | --- | --- | --- |
| valid_baseline | 0.5056 | 0.3666 | 0.3789 | 0.9551 | 6751 | 23252 |
| valid_degraded | 0.5001 | 0.3667 | 0.3791 | 0.9547 | 6396 | 23607 |

점수 평균만 보면 두 데이터셋 차이가 작아 보입니다. 하지만 `high_risk` 예측은 품질 저하 validation 데이터셋에서 더 줄어듭니다. 이 변화는 임계값 근처의 샘플이 어떻게 이동했는지, 특정 입력 오류가 어떤 방향으로 점수를 흔들었는지 추가로 확인해야 한다는 신호입니다.

예측 분포를 지표와 함께 보면 FP 증가를 더 구체적으로 설명할 수 있습니다.

| 관측값 | QA 해석 |
| --- | --- |
| 품질 저하 validation 데이터셋의 `high_risk` 예측 감소 | 같은 임계값에서 관심 클래스(Positive class)로 분류된 샘플이 줄어듦 |
| 품질 저하 평가 데이터셋의 FP 증가 | 관심 클래스 예측 안에 실제 비교 클래스(Negative class)가 새로 포함됨 |
| 정밀도 하락 | 관심 클래스 예측의 신뢰도가 낮아짐 |
| PR-AUC 하락 | 임계값 하나가 아니라 관심 클래스 탐지 품질도 약화된 후보 |

**QA 보고에서는 점수 평균 하나만 쓰지 않습니다.** 평균, 분위수, 예측 분포, FP/FN을 함께 보고 “어떤 현상이 실제 품질 판단을 바꾸는가”를 설명해야 합니다.

## 2-5-3. 데이터 품질 신호와 원인 후보 연결

실습 목표는 품질 저하 validation 데이터셋의 데이터 품질 신호를 지표 변화의 원인 후보로 연결하는 것입니다. 2-2 Great Expectations Demo에서는 `vital_signs_valid_degraded.csv`에서 `heart_rate` 결측값과 `oxygen_saturation` 범위 오류가 확인되었습니다. 2-5에서는 같은 신호를 모델 평가 결과와 함께 읽습니다.

현재 품질 저하 validation 데이터셋의 주요 품질 신호는 다음과 같습니다.

| 품질 신호 | 관측값 | 지표 영향 후보 |
| --- | --- | --- |
| `heart_rate` 결측값 | 1501건, 5.00% | 입력 정보 부족, 점수 불안정, FN 또는 FP 변화 |
| `oxygen_saturation` 범위 오류 | 1201건, 4.00% | 점수 분포 왜곡, FP 증가 후보 |
| 허용 라벨 기준 | 허용되지 않은 라벨 0건, 라벨 결측 0건 | 정답 기준 자체의 실패는 아님 |
| 일부 라벨 반전(label flip) | 교육용 품질 저하 validation 데이터셋 생성 과정에 포함 | 허용 라벨 검증으로는 잡히지 않는 정답 기준 흔들림 후보 |
| 품질 저하 validation 데이터셋 FP 증가 | 110건 | 정밀도 하락과 연결 |
| 품질 저하 validation 데이터셋 FN 증가 | 9413건 | 재현율 하락과 연결 |

**이 표에서 중요한 것은 원인을 단정하지 않는 것입니다.** `oxygen_saturation` 범위 오류가 있으니 FP 증가의 원인이라고 바로 결론 내리면 안 됩니다. 대신 “범위 오류가 점수 분포를 흔들어 FP 증가에 영향을 주었는지 확인한다”처럼 원인 후보와 추가 확인을 분리해야 합니다. 라벨 반전도 마찬가지입니다. 값이 `high_risk`, `low_risk` 중 하나라면 허용 라벨 검증은 통과할 수 있지만, 정답 기준이 일부 흔들렸을 가능성은 별도로 남겨야 합니다.

원인 후보를 정리할 때는 다음 순서가 좋습니다.

| 순서 | 확인 질문 | 확인 근거 |
| --- | --- | --- |
| 1 | 데이터 품질 신호가 있는가 | 결측값, 범위 오류, 라벨 기준 |
| 2 | 예측 분포가 달라졌는가 | `high_risk`, `low_risk` 예측 건수 |
| 3 | 오류 유형이 달라졌는가 | FP, FN 변화 |
| 4 | 점수 구분력도 약해졌는가 | AUROC, PR-AUC |
| 5 | 원인 후보를 어디까지 좁힐 수 있는가 | 입력 품질, 라벨, 임계값, 모델 버전 |

이 순서를 따르면 모델 수정부터 시작하는 오류를 줄일 수 있습니다. 데이터 품질, 예측 분포, 오류 유형을 함께 확인한 뒤에야 모델 변경, 데이터 정리, 임계값 검토 중 무엇이 필요한지 판단할 수 있습니다.

## 2-5-4. QA 코멘트로 정리하기

실습 목표는 관측값을 QA 코멘트로 바꾸는 것입니다. Lab 출력은 숫자를 보여주지만, QA 보고에는 숫자와 판단 조건이 함께 들어가야 합니다. 특히 품질 저하 validation 데이터셋 결과를 보고할 때는 데이터 품질 신호, 지표 변화, 추가 확인을 분리해서 적습니다.

보고서용 비교 리포트에서 확인한 값을 사용하면 QA 코멘트는 다음과 같이 쓸 수 있습니다. **이 문장은 그대로 제출하기보다 현재 실행 결과와 artifact 경로를 확인한 뒤 보고서 문장으로 다듬어야 합니다.**

```text
같은 기준선 모델과 임계값 `0.50`에서 기준 validation 데이터셋과 품질 저하 validation 데이터셋을 비교했습니다.
품질 저하 validation 데이터셋에서는 `heart_rate` 결측값 1501건, `oxygen_saturation` 범위 오류 1201건이 확인되었습니다.
교육용 품질 저하 validation 데이터셋 생성 과정에는 일부 라벨 반전(label flip)도 포함되어 있습니다.

모델 평가 결과, 정밀도는 1.0000에서 0.9828로 낮아졌고
PR-AUC는 0.7999에서 0.7806로 낮아졌습니다.
FP는 0건에서 110건으로 증가했고, FN은 9017건에서 9413건으로 증가했습니다.

QA 판단:
입력 특성(feature) 품질 저하가 점수와 예측 분포를 흔들었을 가능성이 있습니다.
모델 자체 문제로 단정하지 않고, 점수 분포와 오류가 발생한 행(row)을 추가 확인합니다.
```

이 코멘트는 “모델 자체가 나쁘다”로 끝나지 않습니다. 같은 모델과 임계값이라는 비교 조건을 밝히고, 데이터 품질 신호와 지표 변화의 연결을 설명한 뒤, 추가 확인 항목을 남깁니다.

실패 시 확인 포인트는 다음과 같습니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 모델 파일을 찾지 못함 | 2-4-1 기준선 학습 실행 여부 |
| 기준/품질 저하 validation 데이터셋 숫자가 문서와 다름 | `labs/prepare_data.py` 재실행 여부와 데이터 파일 변경 여부 |
| 점수 분포 계산 실패 | 특성 컬럼 목록과 모델 입력 컬럼 일치 여부 |
| FP/FN 해석이 반대로 보임 | 관심 클래스가 `high_risk`인지 확인 |

2-5의 결론은 데이터 품질과 모델 지표를 한 문장으로 연결하는 것입니다. “품질 저하 데이터셋에서 FP가 증가했다”는 관측은 “입력 품질 저하가 관심 클래스 예측을 늘리고 정밀도를 낮췄을 가능성”이라는 원인 후보로 이어집니다. 다음 확인은 이 비교 조건을 실험 기록으로 남기는 일입니다.
