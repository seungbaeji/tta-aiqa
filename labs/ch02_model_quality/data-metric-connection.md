# 2-5. 데이터 품질과 성능 지표의 연결

2-5 Lab의 목표는 데이터 품질 저하와 모델 지표(metric) 변화를 하나의 QA 설명으로 연결하는 것입니다. 2-4에서 같은 모델을 기준 validation 데이터셋과 품질 저하 validation 데이터셋에 적용했다면, 2-5에서는 그 결과를 점수(score) 분포, 예측(prediction) 분포, FP/FN 변화와 연결해 원인 후보를 정리합니다.

여기서 `vital_signs_valid_degraded.csv`는 현재 운영 입력 샘플의 실패 양상을 validation 기준에서 교육용으로 재현한 비교 artifact입니다. 따라서 2-5의 목적은 “degraded 파일이 실제 운영 데이터다”라고 주장하는 것이 아니라, 운영 입력 변화가 생겼을 때 같은 모델과 같은 threshold에서 어떤 지표와 분포를 함께 봐야 하는지 연습하는 것입니다.

이 Lab의 핵심은 데이터 품질 신호와 지표 변화를 같은 원인 후보 설명으로 묶는 것입니다. 문서는 관측값을 어떻게 읽을지 설명하고, Notebook은 같은 흐름을 셀 단위로 실행합니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/02_model_quality/data-metric-connection.md` | 데이터 품질 신호와 지표 변화 해석 |
| 초급 Notebook | `labs/ch02_model_quality/02_precision_recall.ipynb` | 기준 데이터셋과 품질 저하 데이터셋의 FP/FN, Precision, Recall 비교 |
| 초급 Notebook | `labs/ch02_model_quality/03_read_metric_record.ipynb` | metric 기록에서 데이터셋, 모델 버전, threshold 조건 확인 |
| Lite Notebook | `jupyterlite/files/02_model_quality/02_precision_recall.ipynb` | 브라우저에서 지표와 오류 유형 비교 |
| Lite Notebook | `jupyterlite/files/02_model_quality/03_read_metric_record.ipynb` | 브라우저에서 metric 기록 확인 |
| 참고 Notebook | `labs/ch02_model_quality/07_data_metric_connection_lab.ipynb` | 전체 데이터-지표 연결 흐름을 한 번에 다시 볼 때 사용 |
| 비교 JSON artifact | `artifacts/experiments/chapter_02/validation_degradation_comparison.json` | validation 기준/품질 저하 평가 metrics, delta, score/prediction distribution, threshold analysis 확인 |
| 보고서용 비교 리포트 | `artifacts/reports/chapter_02_model_quality_comparison.md` | 릴리스 회의 보고서에 인용할 비교표와 QA 판단 확인 |
| CLI 재실행 경로 | `make lab-model-quality` | 기준선 모델과 2장 비교 산출물 재생성 |

!!! note "브라우저 실습"
    설치 없이 확인하려면 <a href="../../jupyterlite/lab/index.html?path=02_model_quality/02_precision_recall.ipynb">JupyterLite에서 Precision과 Recall 확인</a>을 열고, 이어서 <a href="../../jupyterlite/lab/index.html?path=02_model_quality/03_read_metric_record.ipynb">metric 기록 확인</a>을 엽니다. 이 경로에서 확인한 값은 prepared evidence 기반의 브라우저 실습 결과로 기록합니다.

Notebook으로 실습한다면 `labs/ch02_model_quality/02_precision_recall.ipynb`를 먼저 열고, 이어서 `labs/ch02_model_quality/03_read_metric_record.ipynb`를 실행합니다. 명령행에서는 `make lab-model-quality`로 2-4-2 기준선 모델과 2장 비교 산출물을 다시 만들 수 있습니다. 읽기 전용 확인에서는 `validation_degradation_comparison.json`과 보고서용 Markdown을 열어 기준 validation 데이터셋과 품질 저하 validation 데이터셋의 지표, 점수 분위수, 예측 분포를 확인합니다.

## 2-5-1. 기준 데이터셋과 품질 저하 데이터셋 비교

실습 목표는 2-4에서 확인한 지표 변화를 출발 관측값으로 고정하는 것입니다. 기준 데이터는 `vital_signs_valid_baseline.csv`이고, 품질 저하 비교용 데이터는 `vital_signs_valid_degraded.csv`입니다. 이 비교용 데이터는 현재 운영 입력 샘플에서 나타날 수 있는 결측과 범위 오류를 validation 기준에서 재현한 교육용 데이터입니다.

**이 비교에서 중요한 전제는 모델과 임계값(threshold)을 고정한다는 점입니다.** 모델 버전이나 임계값이 함께 바뀌면 지표 변화의 원인을 데이터 품질로 보기 어렵습니다. 2-5는 데이터 조건 변화에 집중하므로 2-4에서 만든 기준선 모델과 운영 임계값 `0.50`을 그대로 사용합니다.

이 실행에서 확인할 핵심은 같은 모델과 threshold에서 데이터 조건 변화만 비교했는지입니다. Notebook에서는 `labs/ch02_model_quality/02_precision_recall.ipynb`의 지표 비교 셀과 `03_read_metric_record.ipynb`의 조건 확인 셀을 실행합니다. 명령행에서 전체 Lab 산출물을 다시 만들 때는 `make lab-model-quality`를 사용합니다. 이미 준비된 artifact가 있다면 `artifacts/reports/chapter_02_model_quality_comparison.md`에서 같은 비교표를 먼저 확인합니다.

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

보고서용 비교 리포트에서 확인한 값을 사용하면 QA 코멘트는 비교 조건, 관측값, 판단, 다음 확인으로 나누어 작성합니다. Notebook의 마지막 셀은 이 구조에 맞춰 보고 문장 초안을 만들지만, 그대로 제출하기보다 현재 실행 결과와 artifact 경로를 확인한 뒤 문장을 다듬어야 합니다.

| 구분 | 보고서에 남길 핵심 |
| --- | --- |
| 비교 조건 | 같은 기준선 모델과 임계값 `0.50`에서 기준 validation 데이터셋과 품질 저하 validation 데이터셋 비교 |
| 데이터 품질 신호 | `heart_rate` 결측값 1501건, `oxygen_saturation` 범위 오류 1201건, 일부 라벨 반전 후보 |
| 지표 변화 | 정밀도 `1.0000 → 0.9828`, PR-AUC `0.7999 → 0.7806`, FP `0 → 110`, FN `9017 → 9413` |
| QA 판단 | 입력 특성 품질 저하가 점수와 예측 분포를 흔들었을 가능성을 원인 후보로 남김 |
| 다음 확인 | 모델 자체 문제로 단정하지 않고 점수 분포와 오류 발생 행을 추가 확인 |

이 코멘트는 “모델 자체가 나쁘다”로 끝나지 않습니다. 같은 모델과 임계값이라는 비교 조건을 밝히고, 데이터 품질 신호와 지표 변화의 연결을 설명한 뒤, 추가 확인 항목을 남깁니다.

실패 시 확인 포인트는 다음과 같습니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 모델 파일을 찾지 못함 | 2-4-2 기준선 학습 실행 여부 |
| 기준/품질 저하 validation 데이터셋 숫자가 문서와 다름 | `labs/prepare_data.py` 재실행 여부와 데이터 파일 변경 여부 |
| 점수 분포 계산 실패 | 특성 컬럼 목록과 모델 입력 컬럼 일치 여부 |
| FP/FN 해석이 반대로 보임 | 관심 클래스가 `high_risk`인지 확인 |

2-5의 결론은 데이터 품질과 모델 지표를 한 문장으로 연결하는 것입니다. “품질 저하 데이터셋에서 FP가 증가했다”는 관측은 “입력 품질 저하가 관심 클래스 예측을 늘리고 정밀도를 낮췄을 가능성”이라는 원인 후보로 이어집니다. 다음 확인은 2-4에서 남긴 test 평가 기록과 2-5의 validation 비교 artifact를 함께 읽어, 모델 버전과 임계값 조건이 추적 가능한지 확인하는 일입니다.
