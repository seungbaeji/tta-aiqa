# Chapter 03 Serving Inspection Evidence

이 파일은 Docker daemon 또는 Kubernetes cluster를 사용할 수 없는 수강생이 3장 보고서에 남길 수 있는 prepared inspection 근거입니다. 이 내용은 live 실행 결과가 아니라 파일 기준 확인 결과입니다.

## Dockerfile

| 항목 | 확인값 | QA 해석 |
| --- | --- | --- |
| 모델 산출물 | `artifacts/models/chapter_02_baseline.pkl` | 2장 기준선 모델이 이미지에 포함되도록 정의되어 있습니다 |
| 모델 버전 | `MODEL_VERSION=v1` | 기본 응답과 로그에서 `v1`을 노출하도록 정의되어 있습니다 |
| 임계값 | `MODEL_THRESHOLD=0.5` | 2장 평가 기준 임계값과 연결됩니다 |
| 이벤트 로그 | `EVENT_LOG_PATH=artifacts/logs/prediction_events.jsonl` | 예측 이벤트가 구조화 로그로 남도록 정의되어 있습니다 |

Dockerfile inspection만으로는 실행 중 `/health`와 `/predict` 응답을 검증했다고 말할 수 없습니다.

## Kubernetes Manifest

| 항목 | 확인값 | QA 해석 |
| --- | --- | --- |
| ConfigMap | `MODEL_VERSION=v1`, `MODEL_THRESHOLD=0.5`, `API_PORT=8000`, `EVENT_LOG_PATH=artifacts/logs/prediction_events.jsonl` | 운영 설정값의 선언 위치가 확인됩니다 |
| Deployment | 이미지 `ai-quality-serving:chapter-03`, `envFrom`, readinessProbe `/health` | 설정 주입과 준비 상태 기준이 정의되어 있습니다 |
| Service | `port: 80`, `targetPort: 8000` | Service 포트와 컨테이너 포트 연결이 정의되어 있습니다 |

Manifest inspection만으로는 Pod가 Ready 상태인지, Service를 통해 API 호출이 성공했는지, 실행 중 응답의 `threshold`가 0.5인지 검증했다고 말할 수 없습니다.

## Report Boundary

보고서에는 다음처럼 씁니다.

```text
Docker/Kubernetes live smoke test는 실행하지 않았습니다.
파일 inspection 기준으로 Dockerfile은 `chapter_02_baseline.pkl`, `MODEL_VERSION=v1`, `MODEL_THRESHOLD=0.5`를 포함하고, Kubernetes manifest는 ConfigMap, Deployment, Service를 통해 같은 설정 흐름을 정의합니다.
따라서 의도된 배포 설정은 2장 평가 기준과 연결되지만, live response와 Pod readiness는 미검증 상태입니다.
```
