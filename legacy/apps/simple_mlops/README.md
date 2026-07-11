# Simple MLflow + FastAPI MLOps Demo

MLflow tracking, model training, FastAPI serving, fake traffic, Prometheus metrics, structured logs, OTLP trace 전송을 한 번에 확인하는 demo입니다.

## 1. 데이터 준비

### 1-1. 원본 CSV에서 파생 데이터 생성

repository root에서 파생 데이터를 먼저 생성합니다.

```bash
uv run python scripts/prepare_data.py
```

이 명령은 `data/human_vital_signs_dataset_2024.csv`에서 아래 파일을 만듭니다.

```text
data/vital_signs_train.csv
data/vital_signs_test.csv
data/serving_requests.csv
data/serving_requests_current.csv
data/serving_requests_invalid.csv
```

데이터 생성 로직은 `packages/aiqa-data`에 있고, `scripts/prepare_data.py`는 실행용 wrapper입니다.

## 2. 빠른 실행

### 2-1. 전체 stack 실행

```bash
cd apps/simple_mlops
docker compose --profile continuous build
docker compose --profile continuous up -d
```

상태와 로그를 확인합니다.

```bash
docker compose ps
docker compose logs -f trainer-loop traffic-loop api
```

처음에는 trainer가 모델 파일을 만들 때까지 API health가 잠시 `starting`일 수 있습니다.

### 2-2. 작은 VM에서 한 번씩 실행

작은 VM에서는 한 번만 실행하는 흐름을 먼저 사용합니다.

```bash
docker compose up -d mlflow
docker compose --profile train run --rm trainer
docker compose up -d api
docker compose --profile traffic run --rm traffic
```

## 3. 서비스

| 서비스 | 역할 |
| --- | --- |
| `mlflow` | 학습 run, metric, model artifact 저장 |
| `trainer` | `train.py`를 한 번 실행해 모델을 학습하고 MLflow에 기록 |
| `trainer-loop` | `train.py`를 반복 실행해 최신 모델을 계속 갱신 |
| `api` | `models/latest_model.joblib`을 읽어 FastAPI로 예측 제공 |
| `traffic` | `send_fake_traffic.py`로 운영 요청 샘플 전송 |
| `traffic-loop` | 운영 요청을 반복 전송 |
| `alloy` | log, metric, trace를 Grafana Cloud로 전송 |

### 3-1. Package 경계

`apps/simple_mlops`에 남아 있는 Python 파일은 실행 조립을 담당합니다.

| 파일 | 역할 |
| --- | --- |
| `app.py` | FastAPI route, request/response 처리, model loading orchestration |
| `train.py` | trainer CLI argument parsing, `aiqa-model` 호출 |
| `send_fake_traffic.py` | demo traffic 전송 |
| `config.py` | runtime 설정 |

재사용 로직은 repository root의 `packages/` 아래로 분리되어 있습니다.

| Package | 역할 |
| --- | --- |
| `aiqa-core` | feature, label, threshold 계약 |
| `aiqa-model` | sklearn 학습, 평가, 저장, MLflow logging |
| `aiqa-observability` | JSONL event, `/metrics`, OTLP trace helper |

## 4. 확인 URL

| UI | 주소 |
| --- | --- |
| MLflow | `http://localhost:5002` |
| FastAPI docs | `http://localhost:8000/docs` |
| API health | `http://localhost:8000/health` |
| Prediction events | `http://localhost:8000/events` |
| Prometheus metrics | `http://localhost:8000/metrics` |

MLflow 컨테이너 내부 포트는 `5000`이고, host에서는 기본 `5002`로 엽니다.

포트 충돌이 있으면 host port만 바꿉니다.

```bash
MLFLOW_HOST_PORT=5003 API_HOST_PORT=8001 docker compose --profile continuous up -d
```

## 5. 한 번만 실행

계속 도는 loop 없이 학습, serving, traffic을 한 번씩 확인합니다.

```bash
docker compose up -d mlflow
docker compose --profile train run --rm trainer
docker compose up -d api
docker compose --profile traffic run --rm traffic
```

요청을 직접 보내려면:

```bash
curl -s http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "heart_rate": 92,
    "respiratory_rate": 16,
    "body_temperature": 36.8,
    "oxygen_saturation": 95.4,
    "systolic_blood_pressure": 130,
    "diastolic_blood_pressure": 82
  }' | python -m json.tool
```

## 6. 설정

API 설정은 `pydantic-settings`로 읽습니다. Compose 기본값은 `APP_CONFIG_PATH=/app/config/app.local.json`입니다.

| 설정 | 용도 |
| --- | --- |
| `APP_CONFIG_PATH` | JSON 설정 파일 경로 |
| `MODEL_PATH`, `METADATA_PATH`, `EVENTS_PATH` | 모델, metadata, prediction JSONL 경로 |
| `BASELINE_DATA_PATH` | `/metrics`의 input histogram/mean delta baseline CSV |
| `SERVICE_NAME`, `DEPLOYMENT_ENVIRONMENT` | log/metric/trace label |
| `OTLP_TRACES_ENDPOINT` | OTLP/HTTP trace endpoint |
| `INPUT_DISTRIBUTION_FEATURES`, `SCORE_BUCKETS` | comma-separated 또는 JSON 배열 스타일 override |

## 7. Grafana Cloud

Grafana Cloud로 전송하려면 repository root의 `.env`를 준비합니다.

```bash
cd ../..
cp .env.example .env
```

`.env`에서 placeholder 값을 Grafana Cloud stack 값으로 바꿉니다.

Alloy까지 함께 실행합니다.

```bash
cd apps/simple_mlops
OTLP_TRACES_ENDPOINT=http://alloy:4318/v1/traces \
  docker compose --profile continuous --profile observability up -d --build
```

Alloy는 `alloy.cloud.example.alloy`를 사용해 다음 신호를 전송합니다.

| 신호 | 경로 |
| --- | --- |
| structured log | `events/predictions.jsonl` -> Loki |
| metric | API `/metrics` -> Prometheus remote write |
| trace | API OTLP/HTTP -> Alloy -> Tempo |

## 8. 생성 파일

| 경로 | 내용 |
| --- | --- |
| `models/latest_model.joblib` | FastAPI가 읽는 최신 모델 |
| `models/latest_metadata.json` | 학습 run id, metric, threshold |
| `events/predictions.jsonl` | API prediction event |
| `events/fake_traffic_responses.jsonl` | fake traffic 응답 |
| Docker volume `simple_mlops_mlflow-data` | MLflow DB와 artifacts |

## 9. 정리

```bash
docker compose down
```

MLflow DB와 생성 파일까지 지우려면:

```bash
docker compose down -v
rm -rf models events
```
