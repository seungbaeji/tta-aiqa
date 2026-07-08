# 3-6. Train-Serving Skew와 서빙 일치성 검증

학습-서빙 불일치(Train-Serving Skew) 검증은 2장에서 평가한 기준이 API 실행 환경에서도 유지되는지 확인하는 단계입니다. API가 정상 응답을 반환해도 특성(feature) 목록, 전처리 방식, 예측 클래스(class) 기준, 임계값(threshold)이 달라지면 운영 품질은 평가 결과와 다르게 나타날 수 있습니다.

3-6에서는 새로운 모델을 학습하지 않습니다. 학습과 평가 기준을 서빙 기준과 나란히 비교하고, 차이가 있을 때 어떤 품질 문제가 생기는지 판단합니다.

3-6에서 확인할 기준은 다음과 같습니다.

- 특성 목록: 학습 때 사용한 특성이 API 입력에도 있는지 확인
- 특성 순서: 배열 기반 입력에서 순서가 바뀌지 않았는지 확인
- 전처리 방식: 결측값 처리, 스케일링(scaling), 인코딩(encoding)이 같은지 확인
- 운영 기준: 임계값과 모델 버전(model_version)이 평가 기준과 맞는지 확인

3장의 상황으로 보면, `/predict`가 200 OK를 반환하는 것과 학습 기준이 유지되는 것은 다른 문제입니다. 아래처럼 기준선과 서빙 설정을 나란히 놓아야 어떤 값이 같은지, 어떤 값이 운영에서 바뀔 수 있는지 보입니다.

| 비교 항목 | 2장 평가 기준 | 3장 서빙 기준 | QA 판단 |
| --- | --- | --- | --- |
| 모델 산출물(model artifact) | `chapter_02_baseline.pkl` | `MODEL_PATH` | 같은 파일인지 확인 필요 |
| 특성 목록 | `model_features.yaml`의 6개 특성 | `PredictionPayload`의 6개 입력 필드(field) | 누락과 추가 여부 확인 |
| 임계값 | `operating_threshold: 0.5` | `MODEL_THRESHOLD=0.5` | 실행 중 응답값으로 재확인 |
| 예측 클래스 | `low_risk`, `high_risk` | 응답의 `prediction` | 평가와 같은 클래스 값 사용 여부 확인 |

이 표에서 중요한 것은 모든 값이 파일에 존재한다는 사실이 아니라, 배포 후 실제 응답과 로그에서 다시 확인할 수 있어야 한다는 점입니다. 3-6은 이 비교를 배포 전후 체크로 바꾸는 절입니다.

## 3-6-1. Train-Serving Skew의 의미

학습-서빙 불일치(Train-Serving Skew)는 학습과 평가 때 사용한 기준과 서빙 때 사용하는 기준이 달라지는 문제입니다. 모델 자체가 같아도 특성 목록, 전처리 방식, 예측 클래스 기준, 임계값 중 하나만 달라지면 운영 품질이 달라질 수 있습니다.

이 문제는 운영 품질 해석에서 중요한 확인 대상입니다. 오프라인 평가(offline evaluation)에서는 기준을 충족한 지표(metric)가 나왔는데 운영에서는 예측 분포(prediction distribution)나 오류 유형이 달라질 수 있습니다. 이때 원인은 모델 자체 변화가 아니라 학습 때 보던 입력과 운영에서 받는 입력의 차이일 수 있습니다.

[Hidden Technical Debt in Machine Learning Systems](https://proceedings.neurips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html)는 ML 시스템에서 데이터 의존성, 설정 의존성, 파이프라인(pipeline) 간 결합이 장기적인 품질 문제로 나타날 수 있음을 설명합니다. 학습-서빙 불일치는 이 의존성이 운영에서 드러나는 대표 사례입니다. 학습 코드는 그대로여도 특성 생성 위치, 전처리 방식, 설정 주입 방식이 달라지면 오프라인 지표와 서빙 품질이 서로 다른 이야기를 할 수 있습니다.

| 불일치 유형 | 예시 | 영향 |
| --- | --- | --- |
| 특성 목록 차이 | 학습 특성이 API 페이로드(payload)에 없음 | 점수(score) 계산 오류 또는 지표 해석 제한 |
| 특성 순서 차이 | 배열 기반 모델 입력 순서 변경 | 엉뚱한 특성으로 점수 계산 |
| 전처리 차이 | 학습 때 스케일링 적용, 서빙 때 미적용 | 점수 분포 변화 |
| 파생 특성 차이 | 학습 때 `derived_bmi` 사용, 서빙 때 미생성 | 모델 입력 불일치 |
| 임계값 차이 | 평가 0.5, 운영 0.7 | FP/FN 변화 |

QA는 운영 품질 문제가 발생했을 때 모델 파일이나 모델 자체만 의심하지 말고, 서빙 일치성부터 확인해야 합니다. 특히 신규 배포 후 예측 분포가 급격히 바뀌었다면 모델 버전, 임계값, 특성 스키마(feature schema)를 먼저 확인합니다.

## 3-6-2. 특성 목록과 입력 스키마(schema) 일치 확인

`packages/ai-quality/src/ai_quality/serving/domain/skew_check.py`는 학습 특성과 서빙 특성을 비교합니다.

```python
def verify_feature_compatibility(
    training_features: list[str],
    serving_features: list[str],
    training_threshold: float,
    serving_threshold: float,
) -> SkewCheckResult:
    """Check feature and threshold compatibility for serving."""
```

특성 목록 일치는 단순히 이름이 같은지 보는 것을 넘어 순서도 확인해야 합니다. 일부 모델은 특성 이름을 기준으로 처리하지만, 많은 모델은 배열 순서에 의존합니다. 순서가 바뀌면 `heart_rate` 자리에 `oxygen_saturation` 값이 들어가는 식의 문제가 생길 수 있습니다.

실습 기준의 특성은 다음 여섯 개입니다. API 입력 스키마와 이 목록이 맞아야 2장에서 계산한 모델 지표를 서빙 결과와 비교할 수 있습니다.

| 순서 | 학습 특성 | API 입력 필드 |
| --- | --- | --- |
| 1 | `heart_rate` | `heart_rate` |
| 2 | `respiratory_rate` | `respiratory_rate` |
| 3 | `body_temperature` | `body_temperature` |
| 4 | `oxygen_saturation` | `oxygen_saturation` |
| 5 | `systolic_blood_pressure` | `systolic_blood_pressure` |
| 6 | `diastolic_blood_pressure` | `diastolic_blood_pressure` |

아래 결과 항목은 이 목록과 순서, 임계값을 자동 비교했을 때 무엇을 읽어야 하는지 보여줍니다.

| 확인 항목 | 의미 |
| --- | --- |
| `missing_serving_features` | 학습 때 사용했지만 서빙에 없는 특성 |
| `unexpected_serving_features` | 서빙에는 있지만 학습에 없던 특성 |
| `order_matches` | 특성 순서가 학습 기준과 일치하는지 |
| `threshold_matches` | 평가 임계값과 서빙 임계값이 일치하는지 |

QA는 이 결과를 배포 전 체크리스트에 포함해야 합니다. API 간단 확인(smoke test)이 성공해도 특성 순서가 틀리면 점수와 예측(prediction)이 왜곡될 수 있기 때문입니다.

## 3-6-3. 전처리 방식과 파생 특성 일치 확인

3장 실습에서는 파생 특성을 API 입력에서 제외합니다. `configs/validation/model_features.yaml`과 `configs/validation/model_metadata.yaml`의 특성 목록이 일치해야 합니다. 그러나 실무에서는 학습 때 사용한 전처리 로직이 서빙에도 동일하게 적용되는지 확인해야 합니다.

전처리에는 결측값 대체, 스케일링, 인코딩(encoding), 파생 특성 계산이 포함될 수 있습니다. 학습 때 평균값으로 결측값을 대체했는데 서빙에서는 0으로 대체한다면 점수 분포가 달라질 수 있습니다. 학습 때 `derived_bmi`를 계산했는데 서빙에서는 계산하지 않으면 특성 누락이 발생합니다.

| 전처리 항목 | QA 확인 |
| --- | --- |
| 결측값 처리 | 학습과 서빙에서 같은 방식인지 |
| 범주형 인코딩(encoding) | 범주(category) 값 대응이 같은지 |
| 스케일링 | 학습 때 저장한 scaler를 서빙에서 사용하는지 |
| 파생 특성 | 계산식과 단위가 같은지 |

실습에서는 복잡한 전처리 파이프라인(pipeline)을 만들지 않지만, QA 관점은 반드시 이해해야 합니다. 모델이 학습한 입력 변환과 운영 입력 변환이 다르면 오프라인 지표는 운영 품질을 보장하지 못합니다.

## 3-6-4. 예측 클래스와 임계값 설정 일치 확인

정답 라벨(label)은 평가 단계에서 예측이 맞았는지 비교하는 기준입니다. API 요청에는 정답 라벨이 들어오지 않지만, API 응답의 예측 클래스는 평가 때 사용한 `low_risk`, `high_risk`와 같은 값이어야 합니다. 임계값은 점수를 이 예측 클래스로 바꾸는 운영 기준입니다.

따라서 3-6-4에서 확인하는 것은 “API가 정답 라벨을 받는가”가 아닙니다. 평가에서 사용한 클래스 값과 임계값이 서빙에서도 같은 의미로 쓰이는지 확인하는 것입니다.

이 실행은 평가 기준과 서빙 기준의 특성 목록, 순서, 임계값이 일치하는지 확인합니다. 이 스크립트는 `/predict`를 호출하므로 이벤트 로그를 남깁니다. Lab을 반복 실행할 때는 canonical artifact를 오염시키지 않도록 임시 `EVENT_LOG_PATH`를 지정합니다.

```bash
EVENT_LOG_PATH=/tmp/tta-ch03-serving-contract.jsonl \
  uv run --group lab python labs/ch03_serving/check_serving_contract.py
```

이 결과에서 확인할 핵심은 API 호출 성공보다 train-serving 계약 일치 여부입니다. 예상 결과는 다음과 같습니다.

| 결과 | 의미 |
| --- | --- |
| `openapi_has_prediction_payload=True` | OpenAPI에 요청 스키마가 노출됨 |
| `valid_prediction_status=True` | 정상 요청이 200 응답을 반환함 |
| `invalid_payload_rejected=True` | 잘못된 요청이 검증 오류로 차단됨 |
| `train_serving_contract=True` | 특성 목록, 순서, 임계값 기준이 일치함 |

실제 Lab 출력은 다음처럼 기준 일치 여부를 한 줄씩 보여줍니다.

```text
openapi_has_prediction_payload=True
valid_prediction_status=True
invalid_payload_rejected=True
train_serving_contract=True
```

QA 해석에서는 모든 항목이 True인지만 보는 것이 아니라, 실패했을 때 어떤 품질 문제가 발생할지 설명해야 합니다. 특성이 빠지면 점수 계산이 불가능하거나 왜곡될 수 있고, 임계값이 다르면 FP/FN 균형이 달라질 수 있습니다. 예측 클래스 값이 평가와 다르게 표현되면 운영 로그에서 `high_risk` 비율을 비교하기도 어려워집니다. 직접 실행하지 않고 준비된 artifact만 확인했다면 보고서에 “실행은 생략했고 prepared artifact와 설정 파일 기준으로 확인함”이라고 범위를 명시합니다.

실패 시 확인 포인트는 `configs/validation/model_features.yaml`, `configs/validation/model_metadata.yaml`, `configs/operations/serving.yaml`, 환경 변수입니다. 특히 Kubernetes에서는 ConfigMap이나 환경 변수로 임계값이 덮어써질 수 있으므로 실행 중인 값을 확인해야 합니다.
