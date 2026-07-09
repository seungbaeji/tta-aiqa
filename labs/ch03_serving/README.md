# 3장 Container, MLflow, Serving, Kubernetes Lab

3장은 모델을 운영 환경으로 옮기는 전체 흐름을 따라갑니다. Container는 Linux 기반 실행 단위로 가볍게 이해하고, MLflow는 container로 띄워 새 모델의 metric, artifact, model version을 기록합니다. 그 다음 FastAPI와 Compose로 API serving을 확인하고, Kubernetes에서는 MLflow를 먼저 배포한 뒤 Argo CD로 KServe `InferenceService`를 sync하는 흐름을 확인합니다.

이 장의 핵심은 “모델 파일이 있다”가 아니라 “어떤 모델 버전이 어떤 container, API, Kubernetes resource, 관측 필드로 이어지는가”를 설명하는 것입니다.

## 실습 자료

| 구분 | 경로 | 역할 |
| --- | --- | --- |
| README | `labs/ch03_serving/README.md` | 3장 배포 실습 목적, 실행 순서, 확인 기준 |
| Notebook 1 | `labs/ch03_serving/01_container_basics.ipynb` | image/container, Dockerfile, Compose 실행 조건 확인 |
| Script 2 | `demos/ch02_mlflow/01_run_with_docker_mlflow.sh` | MLflow container 실행과 모델 기록 생성 |
| Notebook 3 | `labs/ch03_serving/02_mlflow_model_uri.ipynb` | MLflow candidate URI와 평가 기록 연결 확인 |
| Notebook 4 | `labs/ch03_serving/03_fastapi_compose_serving.ipynb` | FastAPI + Compose 기반 요청/응답 계약 확인 |
| 계약 확인 script | `labs/ch03_serving/04_check_serving_contract.py` | FastAPI 계약 자동 확인과 prediction event 생성 |
| Notebook 5 | `labs/ch03_serving/05_kubernetes_concepts.ipynb` | desired/live state, controller, scheduler, etcd 개념 확인 |
| Notebook 6 | `labs/ch03_serving/06_kubernetes_mlflow_manifest.ipynb` | Kubernetes MLflow Deployment/Service/PVC manifest 확인 |
| Notebook 7 | `labs/ch03_serving/07_argocd_kserve_manifest.ipynb` | Argo CD Application과 KServe InferenceService 핵심 문자열 확인 |
| Notebook 8 | `labs/ch03_serving/08_argocd_gitops_live_check.ipynb` | live sync, KServe Ready, endpoint 확인 항목 정리 |
| GitOps 확인 script | `demos/ch03_docker_kubernetes/scripts/02_check_argocd_manifests.sh` | MLflow/KServe manifest render와 dry-run 확인 |

## 직접 실행 순서

```bash
bash demos/ch02_mlflow/01_run_with_docker_mlflow.sh
docker compose --profile serving up --build serving-api
uv run python labs/ch03_serving/04_check_serving_contract.py
bash demos/ch03_docker_kubernetes/scripts/02_check_argocd_manifests.sh
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-serving
```


## 3-3. FastAPI 기반 예측 API 확인

3-3 Lab의 목표는 제공된 FastAPI 예측 API를 호출하고, 요청/응답 계약(contract)이 모델 품질 확인에 필요한 정보를 담고 있는지 확인하는 것입니다. FastAPI를 처음부터 구현하는 실습이 아니라, 입력 스키마(schema), 정상 응답, 오류 응답을 QA 관점에서 읽는 실습입니다.

3장의 작은 사례로 보면 이 Lab은 `/predict`가 200 OK를 반환할 때 그 응답이 추적 가능한 품질 근거를 담고 있는지 확인하는 단계입니다. **정상 응답에는 `model_version`, `score`, `threshold`, `prediction`, `request_id`가 있어야 하고, 잘못된 입력은 예측 로직으로 들어가기 전에 검증 오류(validation error)로 차단되어야 합니다.**

이 Lab의 핵심은 API 응답과 오류 응답이 품질 추적에 필요한 증거를 남기는지 확인하는 것입니다. 문서는 확인 기준과 예상 결과를 설명하고, Notebook은 같은 API 계약(contract) 확인 흐름을 셀 단위로 실행합니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch03_serving/README.md` | 입력 스키마, 정상 응답, 오류 응답의 QA 해석 확인 |
| 기본 Notebook | `labs/ch03_serving/01_container_basics.ipynb` ~ `08_argocd_gitops_live_check.ipynb` | Container, MLflow, FastAPI, Kubernetes, Argo CD/KServe 흐름을 작은 단계로 확인 |
| FastAPI Notebook | `labs/ch03_serving/03_fastapi_compose_serving.ipynb` | 프로세스 내부 FastAPI client 또는 외부 API로 API 호출과 스키마 확인 실행 |
| CLI 스크립트 | `labs/ch03_serving/*.py` | Notebook과 같은 흐름을 명령행에서 단계별 실행 |

## 3-3-1. 예측 API의 역할

예측 API는 외부 요청을 모델 입력 스키마에 맞게 검증하고, 내부 유스케이스(use case)를 호출해 응답을 반환합니다. 여기서 유스케이스는 요청을 받아 점수(score), 임계값(threshold), 예측(prediction)을 만드는 애플리케이션(application) 흐름입니다. 실습에서는 FastAPI 전체 구현보다 제공 코드에서 API 계약을 읽고 호출하는 데 집중합니다.

API 계약은 요청과 응답의 약속입니다. 어떤 필드(field)가 필요하고, 타입은 무엇이며, 오류가 발생했을 때 어떤 응답이 나오는지 명확해야 합니다. AI 서비스에서는 이 계약이 학습 특성(feature)과도 연결됩니다. API가 받는 특성이 학습 때 사용한 특성과 다르면 점수 품질이 달라질 수 있습니다.

일반 API 계약은 기능의 입력과 출력을 설명합니다. AI API 계약은 여기에 모델 품질 조건이 더해집니다. 입력 필드는 학습 특성과 연결되고, 응답 필드는 `score`, `threshold`, `prediction`, `model_version`처럼 모델 품질 관측에 필요한 값을 포함해야 합니다. 따라서 계약이 불명확하면 단순 연동 오류를 넘어 지표(metric) 해석과 운영 추적이 어려워집니다.

**QA가 API를 확인할 때는 다음 세 가지를 분리해야 합니다.**

| 확인 영역 | 질문 |
| --- | --- |
| 입력 스키마 | 모델에 필요한 특성이 모두 들어오는가 |
| 정상 응답 | `score`, `threshold`, `prediction`, `model_version`이 반환되는가 |
| 오류 응답 | 잘못된 입력이 명확한 검증 오류(validation error)로 처리되는가 |

**예측 API가 정상 응답을 반환한다고 해서 품질 검증이 끝난 것은 아닙니다.** 정상 응답은 기능 관점의 기본 확인이고, 점수와 예측의 품질은 2장 지표와 4장 운영 관측으로 이어져야 합니다.

## 3-3-2. 입력 스키마와 API 계약

FastAPI 입력 스키마는 `packages/ai-quality/src/ai_quality/serving/infrastructure/fastapi_app.py`의 `PredictionPayload`입니다. [FastAPI Request Body 문서](https://fastapi.tiangolo.com/tutorial/body/)는 Pydantic 모델을 사용해 요청 본문(request body)을 정의하고, 그 정의가 자동 API 문서와 검증에 연결되는 흐름을 설명합니다. 이 Lab에서는 그 기능을 FastAPI 사용법 자체보다 API 계약 확인 근거로 사용합니다.

```python
class PredictionPayload(BaseModel):
    """FastAPI request schema for one prediction."""

    request_id: str | None = Field(default=None)
    heart_rate: float
    respiratory_rate: float
    body_temperature: float
    oxygen_saturation: float
    systolic_blood_pressure: float
    diastolic_blood_pressure: float
```

QA는 학습 특성 목록과 API 페이로드(payload) 필드가 일치하는지 확인해야 합니다. 이 확인은 단순 API 테스트가 아니라 Train-Serving Skew를 예방하는 활동입니다.

| 확인 항목 | QA 질문 |
| --- | --- |
| 필수 필드 | 학습 특성의 API 페이로드 포함 여부 |
| 타입 | 숫자 특성의 숫자 타입 입력 여부 |
| 필드 이름 | 학습 특성 이름과 API 필드 이름 대응 일치성 |
| `request_id` | 요청 추적용 ID 존재 여부 |

입력 스키마가 엄격하면 잘못된 요청을 초기에 막을 수 있습니다. 그러나 너무 엄격한 스키마는 실제 운영 데이터의 변동을 처리하지 못할 수 있습니다. 초보자 실습에서는 명확한 필수 특성과 오류 응답 확인에 집중합니다.

## 3-3-3. 제공 코드 확인과 API 호출

정상 요청 Lab은 프로세스 내부 FastAPI client를 사용합니다. 서버를 별도로 띄우지 않아도 요청/응답 계약(contract)을 확인할 수 있습니다.

실습 목표는 FastAPI 앱을 처음부터 구현하는 것이 아닙니다. 제공된 코드를 읽고, 정상 요청을 보내고, 응답에 QA 확인에 필요한 필드가 포함되는지 확인하는 것입니다.

이 단계의 준비 데이터는 정상 요청이 학습 특성 기준을 만족하는지 확인하기 위한 샘플입니다. 준비 데이터는 실습 스크립트에 포함된 샘플 페이로드(sample payload)입니다. 이 페이로드는 모델 특성에 필요한 값을 포함합니다.

이 실행에서 확인할 핵심은 정상 요청이 준비된 운영 로그 artifact를 오염시키지 않고 추적 필드를 남기는지입니다. Notebook에서는 `labs/ch03_serving/03_fastapi_compose_serving.ipynb`의 정상 요청 셀을 실행합니다. 이 셀은 `/predict`를 호출하므로 실행 전 임시 이벤트 로그 경로를 지정합니다. 커널에서 `os.environ["EVENT_LOG_PATH"] = "/tmp/tta-ch03-notebook-events.jsonl"`를 먼저 설정한 뒤 FastAPI client 생성 셀을 실행하면 준비된 운영 로그 artifact를 덮어쓰지 않습니다.

명령행에서 서빙 계약 산출물을 확인할 때도 같은 원칙을 적용합니다. **실행 환경은 저장소 루트의 로컬 shell이고, 다음 명령은 예측 이벤트를 `/tmp` 아래 임시 파일에 남기므로 `artifacts/logs/prediction_events.jsonl`의 준비된 증거를 오염시키지 않습니다.**

```bash
EVENT_LOG_PATH=/tmp/tta-ch03-serving-contract.jsonl \
  uv run python labs/ch03_serving/04_check_serving_contract.py
```

이 출력에서 확인할 핵심은 정상 요청, 오류 요청, train-serving 계약 확인이 모두 통과했는지입니다. 예상 출력은 다음과 같습니다.

```text
openapi_has_prediction_payload=True
valid_prediction_status=True
invalid_payload_rejected=True
train_serving_contract=True
```

예상 응답에는 다음 값이 포함됩니다.

| 응답 필드 | QA 해석 |
| --- | --- |
| `request_id` | 요청 추적 가능성 |
| `model_version` | 의도한 모델 버전 사용 여부 |
| `score` | 점수 분포(score distribution) 관측 대상 |
| `threshold` | 운영 판단 기준 |
| `prediction` | 최종 예측 클래스(class) |

실제 Lab 실행 결과는 다음과 같은 형태입니다. `score` 값은 모델 artifact와 입력 데이터 갱신에 따라 달라질 수 있으므로, 아래 숫자를 정답처럼 외우지 않습니다. 보고서에는 실행한 임시 로그나 Notebook 출력에서 확인한 값을 쓰고, 숫자 자체보다 추적 필드가 모두 있는지 먼저 확인합니다.

```text
status_code=200
{
  "request_id": "lab-03-request-001",
  "model_version": "v1",
  "score": 0.9422,
  "threshold": 0.5,
  "prediction": "high_risk"
}
```

**QA 해석에서는 응답의 숫자 하나를 맞고 틀림으로 판단하지 않습니다.** 이 요청은 정답 라벨(label)이 있는 평가 데이터가 아니라 API 계약 확인용입니다. 따라서 `score`와 `prediction`이 반환되는지, `threshold`와 `model_version`이 추적 가능한지 보는 것이 목적입니다.

정상 요청은 예측 이벤트 로그에도 남습니다. 실습에서는 같은 예시 요청을 반복 실행할 수 있으므로 `lab-03-request-001`이 여러 줄 보일 수 있고, 모델 artifact가 갱신된 뒤에는 같은 `request_id`에 서로 다른 `score`가 남을 수도 있습니다. 이 반복은 Lab 요청과 응답 로그를 연결할 수 있다는 증거이지, 운영 요청 식별자 고유성이나 특정 score 값의 최신성을 검증했다는 뜻은 아닙니다. 운영에서는 요청마다 고유한 `request_id`가 남아야 하며, 이 기준은 4장에서 실제 로그 관측으로 다시 확인합니다.

| 로그 산출물 | 확인할 값 | QA 해석 |
| --- | --- | --- |
| `artifacts/logs/prediction_events.jsonl` | `request_id`, `model_version`, `score`, `threshold`, `prediction` | API 응답을 운영 로그에서 추적 가능 |

**준비된 로그를 그대로 읽은 경우에는 보고서에 “prepared artifact에서 `model_version=v1`, `threshold=0.5`, `score`, `prediction` 필드가 확인됨”이라고 씁니다.** 이때 특정 score 숫자는 append 로그의 최신 실행값이라고 단정하지 않습니다. 직접 스크립트를 실행한 경우에는 “임시 `EVENT_LOG_PATH`로 실행했으므로 canonical log는 변경하지 않음”을 함께 남깁니다.

실패 시 확인 포인트는 모델 산출물(model artifact), 설정 파일, 특성 필드 이름입니다. 특히 2장의 기준선(baseline) 모델이 생성되어 있지 않으면 API가 모델을 로딩하지 못할 수 있습니다.

## 3-3-4. OpenAPI 문서 확인

OpenAPI 문서는 API 계약을 사람이 읽을 수 있게 정리한 문서입니다. FastAPI는 입력 스키마와 응답 스키마를 기반으로 OpenAPI 문서를 자동 생성합니다.

이 실행에서 확인할 핵심은 API 문서가 요청과 응답 계약을 실제 스키마 이름으로 노출하는지입니다. Notebook에서는 `labs/ch03_serving/03_fastapi_compose_serving.ipynb`의 OpenAPI 스키마 확인 셀을 실행합니다.

OpenAPI 스키마에서는 `PredictionPayload`, `PredictionOutput`, `HTTPValidationError`를 확인합니다. QA는 문서화된 스키마가 실제 요청과 일치하는지 확인해야 합니다. 자동 생성된 문서는 테스트 케이스를 만들기 위한 출발점이지, 실제 호출 검증을 대체하지는 않습니다.

| 확인 대상 | QA 관점 |
| --- | --- |
| `PredictionPayload` | 요청 필드와 타입 확인 |
| `PredictionOutput` | 응답에 추적 가능한 필드가 있는지 |
| `HTTPValidationError` | 잘못된 입력이 표준 오류로 표현되는지 |

OpenAPI 확인은 API 개발자만을 위한 작업이 아닙니다. QA는 OpenAPI 문서를 기준으로 테스트 케이스를 만들고, 운영 중 검증 실패(validation failure)가 발생했을 때 어떤 필드가 문제인지 추적할 수 있습니다.

Lab 출력에서는 다음 스키마 이름을 확인합니다.

```text
schema names
- HTTPValidationError
- PredictionOutput
- PredictionPayload
- ValidationError
```

## 3-3-5. 오류 응답 구조 확인

잘못된 입력은 422 검증 오류(validation error)로 반환됩니다. [FastAPI 오류 처리 문서](https://fastapi.tiangolo.com/tutorial/handling-errors/)는 요청 검증 실패가 오류 응답으로 표현되는 방식을 설명합니다. 운영 관점에서는 이러한 실패가 검증 실패 지표나 로그로 연결되어야 합니다.

이 실행에서 확인할 핵심은 잘못된 입력이 예측 로직으로 들어가기 전에 422 검증 오류로 차단되는지입니다. Notebook에서는 `labs/ch03_serving/03_fastapi_compose_serving.ipynb`의 오류 응답 확인 셀을 실행합니다.

**실습 목표는 오류를 일부러 발생시켜 API가 명확하게 실패하는지 확인하는 것입니다.** AI 서비스에서 오류 응답이 불명확하면 데이터 품질 문제와 API 계약 문제를 구분하기 어렵습니다.

| 오류 상황 | 기대 응답 | QA 해석 |
| --- | --- | --- |
| 필수 필드 누락 | 422 검증 오류(validation error) | 스키마 검증이 작동 |
| 숫자 필드에 문자열 입력 | 422 검증 오류(validation error) | 타입 검증이 작동 |
| `request_id` 누락 | 정상 처리 가능 | 서버가 `request_id`를 생성 가능 |

실제 Lab에서는 `heart_rate`에 문자열을 넣고 나머지 필수 필드를 누락한 요청을 보냅니다. 응답은 500 서버 오류가 아니라 422 검증 오류(validation error)입니다.

```text
status_code=422
detail:
- heart_rate: Input should be a valid number, unable to parse string as a number
- respiratory_rate: Field required
- body_temperature: Field required
- oxygen_saturation: Field required
- systolic_blood_pressure: Field required
- diastolic_blood_pressure: Field required
```

실패 시 확인 포인트는 FastAPI 스키마와 Pydantic 검증(validation)입니다. 오류 응답이 500으로 떨어진다면 사용자의 잘못된 입력을 서버 오류로 처리하는 문제가 될 수 있습니다. QA는 잘못된 입력이 예측 로직까지 들어가기 전에 차단되는지 확인해야 합니다.

Lab 전체에서 결과가 예상과 다르면 다음 항목을 먼저 확인합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| API 호출이 500 오류로 실패 | 2장 기준선 모델 파일 `artifacts/models/chapter_02_baseline.pkl` 존재 여부 |
| 정상 응답에 `score`, `threshold`, `prediction`이 없음 | `PredictionOutput` 응답 스키마와 `PredictRisk` 응답 생성 코드 |
| OpenAPI 스키마에 `PredictionPayload`가 없음 | FastAPI 앱 생성 경로와 `/openapi.json` 응답 |
| 오류 요청이 422가 아니라 500으로 실패 | Pydantic 입력 스키마가 예측 로직 전에 동작하는지 |
| `request_id`가 응답에 없음 | 요청에서 전달되었는지, 없을 때 서버가 생성하는지 |

## 3-6. Train-Serving Skew와 서빙 일치성 검증

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
  uv run python labs/ch03_serving/04_check_serving_contract.py
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
