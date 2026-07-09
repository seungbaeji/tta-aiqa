# 2-4. scikit-learn 기반 모델 평가와 기록 실습

## 2-4-1. 실습 버전과 실행 경계

이 실습은 **초급 Notebook 경로**와 **전체 재현 경로**를 모두 제공합니다.

- **초급 Notebook 경로**
  - `score`, `threshold`, `prediction`, Precision, Recall, FP/FN, metric 기록을 작은 셀로 나누어 확인합니다.
  - 강의 중 직접 실행은 이 경로를 기본으로 합니다.

- **전체 재현 경로**
  - 로컬 Python 환경에서 `train/test/valid`를 실제 실행 가능한 상태로 검증하고, `준비 데이터 → 기준선 학습 → test 평가 → validation 비교` 흐름을 재현합니다.
  - 실행 예시는 `09_train_baseline.py`, `10_evaluate_and_record.py`, `11_build_comparison_artifacts.py`입니다.

동일 주제라도 산출물 포인트가 다릅니다.

- 초급 Notebook: 평가 데이터와 지표 해석 흐름을 셀 단위로 확인하고, 수강생이 출력값을 직접 읽습니다.
- 전체 재현 경로: 모델과 비교 artifact를 다시 만들고, 실행 증거의 스코프와 제한 조건을 분리해서 기록합니다.

모델 성능 평가 Lab의 목표는 같은 scikit-learn 모델을 같은 기준으로 평가하고 지표(metric)를 QA 관점에서 읽은 뒤, 그 평가 조건을 기록으로 남기는 것입니다. 2-2에서 확인한 품질 저하 validation 데이터셋의 검증 실패가 실제 지표, 혼동 행렬(Confusion Matrix), 임계값(threshold) 비교에서 어떤 판단 근거로 이어지는지 확인합니다.

이 Lab의 `vital_signs_valid_degraded.csv`는 현재 운영 입력 샘플에서 나타날 수 있는 결측, 범위 오류, 일부 라벨 기준 흔들림을 validation 기준에서 교육용으로 재현한 비교 데이터입니다. 실제 운영 입력 샘플은 4장과 5장에서 운영 holdout 로그와 대시보드 증거로 다시 확인하고, 2장에서는 같은 조건에서 평가 가능한 비교 artifact로 지표 변화를 읽습니다.

이 Lab에서 수강생은 모델을 튜닝하는 사람이 아니라, 평가 결과를 검토하는 품질/운영 담당자 역할을 맡습니다. **핵심 질문은 “성능이 몇 점인가”가 아니라 “같은 모델과 같은 임계값에서 데이터 조건이 달라졌을 때 어떤 오류 유형이 늘었고, 어떤 제한 사항을 QA 코멘트에 남겨야 하는가”입니다.**

이 Lab의 핵심은 scikit-learn 평가 출력과 평가 조건 기록을 같은 QA 판단 흐름으로 묶는 것입니다. 문서는 각 출력의 의미와 QA 해석을 설명하고, Notebook은 같은 흐름을 셀 단위로 실행하는 산출물입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/02_model_quality/evaluation-lab.md` | 실습 목적, 예상 출력, QA 해석 확인 |
| 초급 Notebook 1 | `labs/ch02_model_quality/01_score_threshold.ipynb` | score가 threshold를 지나 prediction이 되는 흐름 확인 |
| 초급 Notebook 2 | `labs/ch02_model_quality/02_precision_recall.ipynb` | Confusion Matrix, Precision, Recall, FP/FN 해석 |
| 초급 Notebook 3 | `labs/ch02_model_quality/03_read_metric_record.ipynb` | 모델 버전, 데이터셋, threshold, metric 기록 확인 |
| 참고 Notebook | `labs/ch02_model_quality/06_model_evaluation_lab.ipynb` | 전체 2장 모델 평가 흐름을 한 번에 다시 볼 때 사용 |
| CLI 학습 스크립트 | `labs/ch02_model_quality/09_train_baseline.py` | 기준선 모델 artifact 생성 |
| 평가 기록 CLI | `labs/ch02_model_quality/10_evaluate_and_record.py` | scikit-learn 기준선 모델의 test metric과 평가 조건 기록 |
| 평가 기록 | `artifacts/experiments/chapter_02/model_test_eval.json` | 선택된 모델과 threshold의 test metric 확인 |
| 비교 기록 | `artifacts/experiments/chapter_02/validation_degradation_comparison.json` | validation 기준/품질 저하 평가 지표, 점수 분포, 예측 분포, 임계값 비교 확인 |
| 보고서용 비교 리포트 | `artifacts/reports/chapter_02_model_quality_comparison.md` | 릴리스 판단 보고서에 인용할 비교표와 QA 판단 확인 |

!!! note "브라우저 실습"
    설치 없이 확인하려면 <a href="../../jupyterlite/lab/index.html?path=02_model_quality/01_score_threshold.ipynb">JupyterLite에서 score와 threshold 확인</a>을 먼저 열고, 이어서 <a href="../../jupyterlite/lab/index.html?path=02_model_quality/02_precision_recall.ipynb">Precision과 Recall 확인</a>, <a href="../../jupyterlite/lab/index.html?path=02_model_quality/03_read_metric_record.ipynb">metric 기록 확인</a>을 엽니다. 이 경로는 브라우저 안에서 실행 가능한 축약 경로이므로, 서버나 전체 artifact를 재생성했다는 근거로 쓰지 않습니다.

실습 흐름은 train split으로 기준선을 만든 뒤, validation split에서 threshold 후보와 품질 저하 비교를 확인하고, 마지막에 test split으로 선택된 모델과 threshold를 평가하는 순서입니다. 이 순서를 지켜야 모델 변경, 데이터 조건 변화, 운영 기준 변경을 서로 섞지 않고 해석할 수 있습니다.

준비된 artifact가 있는 환경에서는 먼저 `model_test_eval.json`과 `validation_degradation_comparison.json`을 확인합니다. `09_train_baseline.py`, `10_evaluate_and_record.py`, `11_build_comparison_artifacts.py`, `make lab-model-quality`는 모델 평가와 비교 산출물을 다시 만들 수 있으므로, 직접 실행하지 않았다면 보고서에는 “prepared artifact에서 확인한 값”이라고 적습니다.

## 2-4-2. scikit-learn 기반 트리 분류 모델 학습

실습 목표는 같은 데이터와 특성(feature)으로 재현 가능한 기준선을 만드는 것입니다. 기준선은 이후 품질 저하 validation 데이터셋, 임계값 변경, 모델 버전 비교의 기준점입니다. 여기서 기준선은 “승인 가능한 모델”이라는 뜻이 아니라, 이후 비교에서 흔들리지 않게 고정해 둘 출발 모델입니다.

이 단계의 준비 데이터와 특성 정의는 이후 평가 조건을 재현하기 위한 기준입니다. 준비 데이터는 `data/vital_signs_train.csv`입니다. 특성 정의는 `configs/validation/model_features.yaml`을 사용하고, 모델 저장 위치는 `artifacts/models/chapter_02_baseline.pkl`입니다. 모델 학습 코드는 `packages/ai-quality/src/ai_quality/model_quality/infrastructure/sklearn_classifier.py`에 있으며, 이 과정에서는 `RandomForestClassifier` 기반 기준선 모델을 사용합니다.

이 실행은 이후 validation 비교와 test 평가에 사용할 기준선 모델 artifact를 생성합니다. 로컬 환경에서 직접 실행할 때는 `labs/ch02_model_quality/09_train_baseline.py`를 사용하고, 읽기 전용 확인에서는 준비된 `artifacts/models/chapter_02_baseline.pkl`의 존재와 평가 기록의 조건을 확인합니다.

이 단계에서 확인할 핵심은 학습 행 수, 특성 목록, 모델 저장 경로가 평가 기록에 남길 조건과 일치하는지입니다. 현재 기준선은 `heart_rate`, `respiratory_rate`, `body_temperature`, `oxygen_saturation`, `systolic_blood_pressure`, `diastolic_blood_pressure`를 입력 특성으로 사용합니다.

수강생은 모델 구조나 하이퍼파라미터를 깊게 수정하지 않습니다. 대신 어떤 데이터셋(dataset), 어떤 특성 목록, 어떤 라벨(label) 기준으로 기준선이 만들어졌는지 확인합니다.

**QA 해석에서 중요한 것은 기준선이 비교 기준이라는 점입니다.** 이후 지표가 좋아졌거나 나빠졌다고 말하려면 먼저 기준 모델이 있어야 합니다. 기준선 없이 새 모델 하나만 평가하면 품질 회귀를 판단하기 어렵습니다.

이 단계에서 QA가 남길 기록은 모델 파일 자체보다 비교 조건입니다. 어떤 데이터셋, 어떤 특성, 어떤 라벨, 어떤 모델 artifact로 이후 지표를 계산했는지 적어야 2-4-3과 2-6에서 결과를 다시 비교할 수 있습니다. 이 조건은 2-4-3의 평가 기록 CLI가 `model_test_eval.json`에 함께 남깁니다.

실패 시 확인 포인트는 다음과 같습니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 데이터 파일을 찾지 못함 | `data` 경로와 `labs/prepare_data.py` 실행 여부를 확인 |
| 특성 컬럼 오류 | `configs/validation/model_features.yaml`과 데이터 컬럼을 비교 |
| 라벨 오류 | `low_risk`, `high_risk` 외 값이 있는지 확인 |
| 모델 저장 실패 | `artifacts/models` 디렉터리 생성 여부를 확인 |

## 2-4-3. test 데이터셋 기반 최종 모델 평가

실습 목표는 학습과 validation에 사용하지 않은 test 데이터셋에서 선택된 모델과 threshold의 지표를 계산하고, 정확도(Accuracy)만이 아니라 정밀도(Precision), 재현율(Recall), 혼동 행렬을 함께 해석하는 것입니다.

이 단계의 준비 데이터와 모델은 선택된 조건을 test 기준으로 검증하기 위한 것입니다. 준비 데이터는 `data/vital_signs_test.csv`이고, 준비 모델은 2-4-2에서 생성한 기준선 모델입니다. 임계값은 validation에서 비교한 후보 중 운영 기준으로 고정한 기본값 `0.50`을 사용합니다. `vital_signs_train.csv`는 기준선 학습에 사용하고, `vital_signs_test.csv`는 선택 이후 최종 모델 평가에만 사용합니다.

이 실행은 같은 scikit-learn 모델의 test metric과 평가 조건을 하나의 기록으로 남깁니다. 강의 중에는 `labs/ch02_model_quality/02_precision_recall.ipynb`와 `03_read_metric_record.ipynb`에서 준비된 평가 기록을 읽습니다. 명령행에서는 먼저 2-4-2의 `09_train_baseline.py`로 기준선 모델을 만들고, 이어서 `10_evaluate_and_record.py`로 `artifacts/experiments/chapter_02/model_test_eval.json`에 기록합니다.

이 단계에서 확인할 핵심은 FP/FN과 주요 metric이 같은 데이터셋, 같은 threshold 조건에서 계산되었는지입니다. 준비 artifact 기준으로 test 데이터셋은 `20002`행이고, threshold `0.50`에서 TP `4455`, FP `0`, FN `5989`, TN `9558`입니다. 주요 지표는 정확도 `0.7006`, 정밀도 `1.0000`, 재현율 `0.4266`, F1 `0.5980`, AUROC `0.7200`, PR-AUC `0.8033`입니다.

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

실패 시 확인 포인트는 모델 파일 존재 여부, 특성 컬럼 일치 여부, 임계값 설정값입니다. 평가 코드가 실행되더라도 라벨 기준이 잘못되면 지표 해석이 틀릴 수 있으므로 허용 라벨 목록도 함께 확인합니다. `model_test_eval.json`이 생성되지 않았다면 `10_evaluate_and_record.py` 실행 결과와 `artifacts/experiments/chapter_02` 경로를 확인합니다.

## 2-4-4. 기준 데이터셋과 품질 저하 데이터셋 비교

실습 목표는 데이터 품질 저하가 지표에 어떤 영향을 주는지 확인하는 것입니다. `vital_signs_valid_degraded.csv`는 현재 운영 입력 샘플의 실패 양상을 교육용으로 재현하기 위해 2-2에서 확인한 결측값(missing value), 범위 오류, 일부 라벨 반전(label flip)을 포함합니다. 라벨 반전은 값은 `high_risk` 또는 `low_risk`처럼 허용 목록 안에 있지만, 정답 기준이 일부 반대로 들어간 상태를 뜻합니다.

이 비교에서 라벨 관련 판단은 두 층으로 나누어야 합니다. 허용 라벨 검증은 지표 계산 형식이 가능한지 확인하고, 라벨 반전 후보는 지표가 실제 품질을 얼마나 믿을 수 있게 반영하는지 확인합니다.

| 구분 | 확인 질문 | 이번 Lab에서의 의미 | 보고서 표현 |
| --- | --- | --- | --- |
| 허용 라벨 검증 | 값이 `high_risk`, `low_risk` 안에 있는가 | 지표 계산 형식은 유지됨 | “허용 라벨 기준은 통과했습니다.” |
| 정답 기준 신뢰 | 일부 행의 정답이 반대로 들어갔을 가능성이 있는가 | FP/FN과 지표 변화를 직접 흔들 수 있음 | “라벨 반전 후보는 별도 제한 사항으로 남깁니다.” |
| 입력 특성 품질 | 결측과 범위 오류가 점수에 영향을 주는가 | 점수와 예측 분포 변화의 원인 후보 | “입력 특성 품질 이슈와 라벨 기준 후보를 분리해 확인합니다.” |

이 단계의 준비 데이터는 같은 모델에서 데이터 조건 변화의 영향을 분리하기 위한 비교 기준입니다. 준비 데이터는 기준 validation 데이터셋과 품질 저하 validation 데이터셋입니다. 같은 모델을 두 데이터셋에 적용해 지표 변화를 비교합니다. 모델이 같기 때문에 지표 변화의 주요 원인 후보는 데이터 차이에서 찾을 수 있습니다.

이 비교는 실행 여부와 관계없이 같은 artifact 값을 기준으로 QA 해석을 만들 수 있어야 합니다. 강의 중에는 `labs/ch02_model_quality/02_precision_recall.ipynb`와 `03_read_metric_record.ipynb`에서 핵심 값만 확인합니다. 읽기 전용으로 확인할 때는 `artifacts/experiments/chapter_02/validation_degradation_comparison.json`과 `artifacts/reports/chapter_02_model_quality_comparison.md`를 열어 같은 값을 확인합니다.

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

## 2-4-5. 임계값 변화에 따른 정밀도/재현율 비교

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

## 2-4-6. 혼동 행렬 표 해석

실습 목표는 혼동 행렬을 숫자로 읽고, FP와 FN이 품질 판단에 어떤 의미를 갖는지 설명하는 것입니다. 2-4-6은 새로운 스크립트를 실행하는 단계가 아니라, 2-4-3과 2-4-5에서 이미 나온 출력을 품질 판단 문장으로 바꾸는 해석 단계입니다.

이 단계의 준비 데이터와 모델은 FP/FN 해석을 앞선 평가 출력과 연결하기 위해 기준선 평가와 동일합니다. 강의 자료에서는 혼동 행렬을 표로 보여주고, 수강생은 TP, FP, FN, TN이 각각 어떤 의미인지 설명합니다.

이 해석 단계의 증거는 2-4-3 평가 스크립트의 `confusion_matrix` 출력입니다. 중요한 것은 그림을 예쁘게 만드는 것이 아니라, 표의 각 칸이 운영 품질에 어떤 의미인지 이해하는 것입니다.

이 구조에서 확인할 핵심은 실제 라벨과 예측 라벨의 조합이 어떤 오류 유형을 만드는지입니다. 예상 결과는 다음과 같은 구조입니다.

|  | 예측 `high_risk` | 예측 `low_risk` |
| --- | --- | --- |
| 실제 `high_risk` | TP | FN |
| 실제 `low_risk` | FP | TN |

**QA 해석에서는 FP와 FN을 따로 설명해야 합니다.** FP가 늘어난 모델과 FN이 늘어난 모델은 같은 정확도를 가질 수 있어도 운영 의미가 다릅니다. 이 차이를 설명하지 못하면 AI QA 보고서가 단순 지표 나열에 머물게 됩니다.

2-4의 최종 코멘트는 조건, 변화, 다음 확인을 분리해서 정리합니다. 예를 들어 같은 기준선 모델과 임계값 `0.50`에서 품질 저하 validation 데이터셋을 비교한 결과, 정밀도는 낮아지고 FP는 증가했습니다. 2-2 검증 리포트에서 확인한 `heart_rate` 결측과 `oxygen_saturation` 범위 오류를 지표 변화의 원인 후보로 남기고, 점수 분포와 예측 분포를 추가 확인합니다.

실패 시 확인 포인트는 라벨 순서입니다. 혼동 행렬을 그릴 때 관심 클래스와 비교 클래스 축이 바뀌면 FP와 FN 해석이 반대로 될 수 있습니다. 반드시 관심 클래스가 `high_risk`인지 확인하고 표를 읽어야 합니다.

## 2-4-7. 평가 조건과 지표 기록

실습 목표는 2-4에서 계산한 scikit-learn 평가 결과를 나중에 비교할 수 있는 기록으로 남기는 것입니다. 모델을 다시 설명하거나 MLflow 사용법을 익히는 단계가 아니라, 같은 모델, 같은 데이터셋, 같은 임계값에서 계산한 지표인지 추적할 수 있게 만드는 단계입니다.

이 단계의 준비 데이터와 모델은 test metric과 비교 조건을 함께 남기기 위해 2-4-3과 같습니다. `10_evaluate_and_record.py`는 `chapter_02_baseline.pkl`을 로드하고, `vital_signs_test.csv`에 대해 `predict_proba`로 score를 만든 뒤, 운영 임계값 `0.50`을 적용해 metric을 계산합니다. 같은 실행에서 `model_test_eval.json`을 만들고, MLflow가 설치된 환경에서는 같은 내용을 `artifacts/mlflow.db`에도 남깁니다.

이 실행은 2-4 모델 평가 결과를 2-6 버전 비교 Demo가 읽을 수 있는 기록으로 만듭니다. 로컬에서 직접 실행할 때는 `labs/ch02_model_quality/10_evaluate_and_record.py`를 사용하고, 읽기 전용 확인에서는 `artifacts/experiments/chapter_02/model_test_eval.json`의 조건과 지표를 확인합니다. 이 기록에는 `vital_signs_test`, threshold `0.50`, confusion matrix, 주요 metric, artifact 경로가 함께 남아야 합니다.

QA 해석에서는 JSON 파일의 존재보다 그 안에 남은 비교 조건을 먼저 확인합니다. `dataset_version`, `feature_columns`, `model_version`, `operating_threshold`, FP/FN이 함께 남아야 이후 버전 비교에서 지표 차이를 모델 변화, 데이터 변화, 임계값 변화 중 어디에 연결할지 판단할 수 있습니다.

실패 시 확인 포인트는 `chapter_02_baseline.pkl` 생성 여부, `vital_signs_test.csv` 존재 여부, MLflow 설치 여부입니다. MLflow가 없어도 JSON 기록은 생성되어야 하며, 이 수업의 필수 근거는 JSON 기록입니다. MLflow tracking DB는 2-6에서 같은 기록을 도구로 확인하는 선택 경로로 다룹니다.
