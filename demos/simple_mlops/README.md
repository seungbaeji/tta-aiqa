# Simple MLflow + FastAPI MLOps Demo

MLflow, model training, FastAPI serving, fake traffic을 한 번에 확인하는 최소 데모입니다.

## 빠른 실행

루트에서 데이터가 아직 준비되지 않았다면 먼저 실행합니다.

```bash
uv run python scripts/course.py prepare-data
```

데모 폴더로 이동해 컨테이너를 시작합니다.

```bash
cd demos/simple_mlops
sudo docker compose --profile continuous build
sudo docker compose --profile continuous up -d
```

상태와 로그를 확인합니다.

```bash
docker compose ps
docker compose logs -f trainer-loop traffic-loop api
```

처음에는 모델 파일이 만들어질 때까지 API health가 잠시 `starting`일 수 있습니다.

작은 VM에서 `continuous` profile이 무겁다면 먼저 한 번만 실행하는 흐름으로 확인합니다.

```bash
docker compose up -d mlflow
docker compose --profile train run --rm trainer
docker compose up -d api
docker compose --profile traffic run --rm traffic
```

## 동작 구조

이 demo는 학습, 추적, serving, traffic 생성을 일부러 나눠 보여줍니다.

| 서비스 | 역할 |
| --- | --- |
| `mlflow` | MLflow tracking server. 학습 run, metric, model artifact를 저장합니다. |
| `trainer-loop` | `train.py`를 반복 실행해 모델을 학습하고 MLflow에 기록합니다. 최신 모델은 `./models/latest_model.joblib`에도 저장합니다. 작은 VM을 위해 5분마다 가볍게 재학습합니다. |
| `api` | FastAPI serving server. MLflow에서 모델을 직접 내려받지 않고 `./models/latest_model.joblib` 파일을 읽어 예측합니다. |
| `traffic-loop` | `send_fake_traffic.py`로 API에 가짜 운영 요청을 계속 보내고 응답을 `./events`에 저장합니다. |

학습에는 MLflow를 사용합니다. 정확히는 `train.py`가 `mlflow.set_tracking_uri("http://mlflow:5000")`로 MLflow server에 연결한 뒤 parameter, metric, sklearn model, metadata artifact를 기록합니다. FastAPI는 MLflow tracking server에 직접 의존하지 않고, trainer가 공유 volume에 저장한 최신 모델 파일을 읽습니다.

API image는 serving에 필요한 패키지만 설치합니다. MLflow client는 `trainer`와 `trainer-loop` image에만 설치하므로, API build가 MLflow 의존성을 내려받느라 오래 걸리면 최신 compose/Dockerfile인지 확인합니다.

```bash
docker compose build api
docker compose --profile train build trainer
```

## 확인 URL

| UI | 주소 |
| --- | --- |
| MLflow | `http://localhost:5002` |
| FastAPI docs | `http://localhost:8000/docs` |
| API health | `http://localhost:8000/health` |
| Prediction events | `http://localhost:8000/events` |
| Prometheus metrics | `http://localhost:8000/metrics` |

MLflow 컨테이너 내부 포트는 계속 `5000`입니다. 그래서 trainer는 Docker network 안에서
`http://mlflow:5000`을 사용하고, 브라우저에서 볼 때만 호스트 포트 `5002`로 접속합니다.
루트 compose의 MLflow가 `localhost:5000`을 쓰는 경우와 충돌하지 않도록 이렇게 분리했습니다.

Windows PC에서 Bastion tunnel로 simple demo를 확인할 때는 원격 VM의 `5002`도 포워딩합니다.

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 5002:127.0.0.1:5002 \
  -L 8000:127.0.0.1:8000 \
  -J mrml-bastion@146.56.41.109 \
  tta@<VM_IP>
```

터널은 Windows PC 터미널에서 실행하고, 브라우저는 `http://127.0.0.1:5002`, `http://127.0.0.1:8000/docs`를 엽니다.

이미 `5002` 또는 `8000`도 사용 중이면 host port만 바꿔 실행합니다. 컨테이너 내부 통신은 그대로라서 학습/서빙 코드는 바꿀 필요가 없습니다.

```bash
MLFLOW_HOST_PORT=5003 API_HOST_PORT=8001 docker compose --profile continuous up -d
```

## 설정 방식

API 설정은 `pydantic-settings`로 읽습니다. 기본 Compose 실행에서는
`APP_CONFIG_PATH=/app/config/app.local.json`을 사용하고, 같은 항목은 환경변수로 덮어쓸 수 있습니다.

| 설정 | 용도 |
| --- | --- |
| `APP_CONFIG_PATH` | JSON 설정 파일 경로. Kubernetes에서는 ConfigMap을 이 경로로 mount합니다. |
| `MODEL_PATH`, `METADATA_PATH`, `EVENTS_PATH` | 모델, metadata, prediction JSONL 경로 override |
| `BASELINE_DATA_PATH` | 입력 분포 baseline CSV. `/metrics`의 input histogram/mean delta에 사용합니다. |
| `SERVICE_NAME`, `DEPLOYMENT_ENVIRONMENT` | Grafana label과 trace resource attribute |
| `OTLP_TRACES_ENDPOINT` | OTLP/HTTP trace 수신 endpoint. 예: `http://alloy:4318/v1/traces` |
| `INPUT_DISTRIBUTION_FEATURES`, `SCORE_BUCKETS` | JSON 배열 환경변수로 override. 예: `'["heart_rate","oxygen_saturation"]'` |

Kubernetes에서는 ConfigMap과 env override를 함께 씁니다.

```yaml
env:
  - name: APP_CONFIG_PATH
    value: /app/config/app.local.json
  - name: OTLP_TRACES_ENDPOINT
    value: http://alloy:4318/v1/traces
volumeMounts:
  - name: api-config
    mountPath: /app/config
    readOnly: true
volumes:
  - name: api-config
    configMap:
      name: simple-mlops-api-config
```

## Grafana Cloud 관측성

초기 dashboard import는 기존 `demos/ch04_grafana_cloud/02_import_dashboard.py` 흐름을 그대로 사용합니다. simple demo 운영 중 발생하는 신호는 API와 Alloy가 보냅니다.

루트 `.env`가 필요합니다. 처음에는 로컬 기본값이 있는 `.env.example`을 복사하고, Grafana Cloud 전용 예시인 `.env.grafanacloud.example`을 이어 붙입니다. 그 다음 `<...>` placeholder를 Grafana Cloud Portal 값으로 바꿉니다. 이 repository에는 실행 확인을 위해 실제 `.env` 파일도 만들어 두었지만, 개인 token은 Git에 커밋하지 않습니다.

```bash
cd ../..
cp .env.example .env
cat .env.grafanacloud.example >> .env
```

이미 `.env`가 있으면 덮어쓰지 말고 아래 값들이 있는지만 확인합니다.

| 값 | simple demo에서 쓰는 곳 |
| --- | --- |
| `GRAFANA_LABEL_SERVICE=ai-quality-serving` | Loki/Prometheus label. dashboard query와 맞춥니다. |
| `GRAFANA_LABEL_ENVIRONMENT=training` | Loki/Prometheus label. 실습 환경 구분에 사용합니다. |
| `GRAFANA_LOKI_PUSH_URL`, `GRAFANA_LOKI_USER`, `GRAFANA_TELEMETRY_TOKEN` | Alloy가 `events/predictions.jsonl` structured log를 Loki로 보낼 때 사용 |
| `GRAFANA_PROM_REMOTE_WRITE_URL`, `GRAFANA_PROM_USER`, `GRAFANA_TELEMETRY_TOKEN` | Alloy가 `/metrics` scrape 결과를 Grafana Cloud Metrics로 보낼 때 사용 |
| `GRAFANA_TEMPO_OTLP_GRPC_ENDPOINT`, `GRAFANA_TEMPO_USER`, `GRAFANA_TELEMETRY_TOKEN` | Alloy가 API trace를 Grafana Cloud Tempo로 보낼 때 사용 |
| `GRAFANA_CLOUD_URL`, `GRAFANA_DASHBOARD_TOKEN` | dashboard import script에서 사용 |

Token은 두 종류만 있으면 됩니다.

| Token | 어디서 발급 | 필요한 권한 | `.env` 키 |
| --- | --- | --- | --- |
| Cloud Access Policy token | Grafana Cloud Portal → Access Policies | `logs:write`, `metrics:write`, `traces:write` | `GRAFANA_TELEMETRY_TOKEN` |
| Grafana Service Account token | Stack **Launch** → Grafana → Administration → Users and access → Service accounts | dashboard/folder 생성 또는 갱신 권한. 실습에서는 `Editor` role 권장 | `GRAFANA_DASHBOARD_TOKEN` |

Endpoint와 user 값은 stack의 각 datasource details에서 가져옵니다.

| 값 | 가져오는 위치 |
| --- | --- |
| `GRAFANA_LOKI_PUSH_URL`, `GRAFANA_LOKI_USER` | Logs/Loki details 또는 Loki Alloy 예시 |
| `GRAFANA_PROM_REMOTE_WRITE_URL`, `GRAFANA_PROM_USER` | Metrics/Prometheus details 또는 Prometheus remote_write 예시 |
| `GRAFANA_TEMPO_OTLP_GRPC_ENDPOINT`, `GRAFANA_TEMPO_USER` | Traces/Tempo details 또는 Tempo Alloy exporter 예시 |
| `GRAFANA_CLOUD_URL` | Cloud Portal의 stack Instance details 또는 Grafana Launch 후 브라우저 주소 |

### Dashboard 생성

simple MLOps demo는 dashboard JSON을 새로 만들지 않고, 4장 Grafana Cloud demo에서 만든 두 dashboard를 그대로 import합니다.

| Dashboard | 파일 | 역할 |
| --- | --- | --- |
| AI Quality Overview | `artifacts/grafana/ai_quality_overview_dashboard.json` | 요청 수, 오류, 지연 시간, score/prediction 분포, 입력 분포 변화를 한 화면에서 확인 |
| AI Quality Details | `artifacts/grafana/ai_quality_details_dashboard.json` | `request_id`, `trace_id`로 validation failure log, correlated log, Tempo trace, service graph를 추적 |

루트에서 먼저 dry-run으로 endpoint와 folder를 확인한 뒤 import합니다.

```bash
cd ../..
uv run python demos/ch04_grafana_cloud/02_import_dashboard.py --dry-run
uv run python demos/ch04_grafana_cloud/02_import_dashboard.py
```

import script는 `.env`의 `GRAFANA_CLOUD_URL`, `GRAFANA_DASHBOARD_TOKEN`, `GRAFANA_FOLDER_UID`, `GRAFANA_FOLDER_TITLE`을 사용합니다. 기본 folder는 `AI Quality`입니다. `GRAFANA_DASHBOARD_TOKEN`은 Grafana instance의 Service Account token이고, Logs/Metrics/Traces 전송용 `GRAFANA_TELEMETRY_TOKEN`과 다릅니다.

Dashboard import는 화면 껍데기와 쿼리를 만드는 단계입니다. live 데이터는 아직 들어가지 않았을 수 있습니다.

### 초기 데이터 적재

초기 데이터 적재는 별도 seed 파일을 Grafana Cloud에 직접 넣는 방식이 아니라, simple MLOps API에 요청을 보내 운영 중 발생한 log, metric, trace를 쌓는 방식입니다.

| 데이터 | 생성 주체 | Grafana Cloud 적재 경로 |
| --- | --- | --- |
| structured log | API가 `/predict` 처리 시 `events/predictions.jsonl`과 stdout에 JSON 기록 | Alloy `loki.source.file` -> Loki |
| metric | API가 메모리에 누적한 요청 통계를 `/metrics`로 노출 | Alloy `prometheus.scrape` -> Prometheus remote_write |
| trace | API가 요청마다 OTLP/HTTP trace 생성 | API -> Alloy `otelcol.receiver.otlp` -> Tempo |
| 입력 분포 baseline | `config/app.local.json`의 `baseline_data_path` CSV | API `/metrics`의 `ai_quality_input_histogram_count`로 노출 |

계속 도는 demo에서는 dashboard import 후 아래처럼 실행합니다.

```bash
cd demos/simple_mlops
OTLP_TRACES_ENDPOINT=http://alloy:4318/v1/traces \
  docker compose --profile continuous --profile observability up -d --build
```

이 명령은 `trainer-loop`, `api`, `traffic-loop`, `alloy`를 함께 띄웁니다. 처음에는 trainer가 모델을 만든 뒤 API health가 통과하고, 이후 `traffic-loop`가 요청을 보내면서 dashboard에 live 데이터가 채워집니다.

작은 VM에서 한 번만 적재하려면 아래 순서를 사용합니다.

```bash
docker compose up -d mlflow
docker compose --profile train run --rm trainer
OTLP_TRACES_ENDPOINT=http://alloy:4318/v1/traces \
  docker compose --profile observability up -d api alloy
docker compose --profile traffic run --rm traffic
```

마지막 `traffic` 실행이 초기 운영 요청 30건을 만들고, 그 요청들이 log/metric/trace 세 신호로 Grafana Cloud에 전송됩니다. 더 많이 채우고 싶으면 count를 늘려 traffic container를 다시 실행합니다.

```bash
docker compose --profile traffic run --rm traffic \
  python send_fake_traffic.py --api-url http://api:8000 --count 200 --sleep 0.1
```

적재 후 로컬에서 먼저 확인합니다.

```bash
curl -s http://localhost:8000/events | python -m json.tool
curl -s http://localhost:8000/metrics | head -40
docker compose logs --tail=80 alloy
```

Grafana Cloud에서는 dashboard 시간 범위를 최근 15분 또는 최근 1시간으로 맞추고 확인합니다. 처음 몇 분 동안 패널이 비어 있으면 `traffic-loop` 로그, API `/metrics`, Alloy UI 또는 logs를 차례로 확인합니다.

API가 남기는 신호는 세 가지입니다.

| 신호 | 위치 |
| --- | --- |
| structured log | `events/predictions.jsonl`과 API stdout. `request_id`, `trace_id`, `score`, `prediction`, `validation_failure` 포함 |
| metric | `/metrics`. 기존 dashboard의 `ai_quality_*` metric 이름을 유지합니다. |
| trace | `OTLP_TRACES_ENDPOINT`가 설정되면 요청마다 OTLP/HTTP trace 전송 |

Grafana Cloud 전송을 켜려면 루트 `.env`에 Grafana Cloud 값을 두고 Alloy profile을 같이 실행합니다.

```bash
OTLP_TRACES_ENDPOINT=http://alloy:4318/v1/traces \
  docker compose --profile continuous --profile observability up -d
```

Alloy는 `alloy.cloud.example.alloy`를 사용해 `events/predictions.jsonl`을 Loki로 보내고, API의 `/metrics`를 scrape해서 Prometheus remote write로 보내며, API가 보낸 trace를 Tempo로 전달합니다.

`.env`에 placeholder가 남아 있으면 dashboard import나 Alloy exporter가 실패하는 것이 정상입니다. 그 경우 Grafana Cloud Portal의 Logs/Metrics/Traces detail 화면에서 URL과 User 값을 다시 복사하고, token scope가 `logs:write`, `metrics:write`, `traces:write`를 포함하는지 확인합니다.

Kubernetes에 올릴 때는 application 설정과 secret을 분리합니다. `APP_CONFIG_PATH`가 가리키는 JSON은 ConfigMap으로 mount하고, Grafana Cloud token과 endpoint는 Secret 또는 external secret으로 주입합니다.

```yaml
env:
  - name: APP_CONFIG_PATH
    value: /app/config/app.local.json
  - name: OTLP_TRACES_ENDPOINT
    value: http://alloy:4318/v1/traces
  - name: GRAFANA_TELEMETRY_TOKEN
    valueFrom:
      secretKeyRef:
        name: grafana-cloud-credentials
        key: telemetry-token
```

## Proxy 서버로 확인

교육장 VM에서는 `domains.csv`의 domain을 통해 Windows PC 브라우저에서 바로 확인할 수 있습니다. 자신의 VM 이름은 보통 `tta14-pve2-lab` 같은 형식입니다.

```bash
awk -F, -v vm="$(hostname)" 'NR == 1 || $1 == vm {print}' ../../domains.csv
```

| `domains.csv` 컬럼 | 확인 URL |
| --- | --- |
| `app_apps` | `https://<app_apps>/docs` |
| `mlflow_apps` | `https://<mlflow_apps>` |

예를 들어 VM이 `tta14-pve2-lab`이면 FastAPI docs는
`https://tta14-pve2.apps.learn.mrml.dev/docs`, MLflow는
`https://mlflow-tta14-pve2.apps.learn.mrml.dev`에서 확인합니다.

Proxy의 MLflow domain은 교육장 기본 host port `5000`을 바라봅니다. simple demo의 기본값은 port 충돌을 피하려고 `5002`이므로, proxy domain으로 MLflow를 보려면 루트 MLflow를 내린 뒤 아래처럼 띄웁니다.

```bash
MLFLOW_HOST_PORT=5000 docker compose --profile continuous up -d
```

## 한 번만 실행

계속 도는 loop 대신 한 번씩만 확인하려면 아래 순서로 실행합니다.

```bash
docker compose up -d mlflow
docker compose --profile train run --rm trainer
docker compose up -d api
docker compose --profile traffic run --rm traffic
```

## 요청 테스트

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

## 생성 파일

| 경로 | 내용 |
| --- | --- |
| `models/latest_model.joblib` | FastAPI가 읽는 최신 모델 |
| `models/latest_metadata.json` | 학습 run id, metric, threshold |
| `events/predictions.jsonl` | API prediction event |
| `events/fake_traffic_responses.jsonl` | fake traffic 응답 |
| Docker volume `simple_mlops_mlflow-data` | MLflow DB와 artifacts |

## 정리

```bash
docker compose down
```

MLflow DB와 생성 파일까지 지우려면:

```bash
docker compose down -v
rm -rf models events
```

## Port 충돌 복구

`Bind for 0.0.0.0:5000 failed: port is already allocated`가 보이면 예전 compose 설정이나 다른 MLflow가 `5000`을 이미 쓰는 상태입니다. 현재 simple demo는 기본 host port가 `5002`이므로, 기존 simple demo 컨테이너를 재생성합니다.

```bash
cd demos/simple_mlops
docker compose down --remove-orphans
docker compose --profile continuous up -d --force-recreate
```

어떤 컨테이너가 포트를 쓰는지 보려면:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
```

## 컨테이너가 137로 종료될 때

`Exited (137)`은 보통 컨테이너가 강제로 kill된 상태입니다. 작은 VM에서는 메모리 부족으로 MLflow나 API가 같이 죽을 수 있습니다. 먼저 VM에서 OOM 여부를 확인합니다.

```bash
docker inspect simple_mlops-api-1 simple_mlops-mlflow-1 \
  --format '{{.Name}} OOMKilled={{.State.OOMKilled}} ExitCode={{.State.ExitCode}}'

docker compose logs --tail=80 mlflow api trainer-loop
free -h
```

복구할 때는 죽은 컨테이너를 정리하고, 최신 가벼운 학습 설정으로 다시 빌드합니다.

```bash
docker compose down --remove-orphans
docker compose --profile continuous build
docker compose --profile continuous up -d
```

그래도 VM 메모리가 부족하면 loop 대신 한 번만 실행하는 흐름을 사용합니다.

## Notebook

결과 조회용 notebook만 열 때 사용합니다.

```bash
uv sync --group notebook
uv run --group notebook jupyter lab results.ipynb
```
