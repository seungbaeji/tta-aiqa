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

## 확인 URL

| UI | 주소 |
| --- | --- |
| MLflow | `http://localhost:5002` |
| FastAPI docs | `http://localhost:8000/docs` |
| API health | `http://localhost:8000/health` |
| Prediction events | `http://localhost:8000/events` |

MLflow 컨테이너 내부 포트는 계속 `5000`입니다. 그래서 trainer는 Docker network 안에서
`http://mlflow:5000`을 사용하고, 브라우저에서 볼 때만 호스트 포트 `5002`로 접속합니다.
루트 compose의 MLflow가 `localhost:5000`을 쓰는 경우와 충돌하지 않도록 이렇게 분리했습니다.

이미 `5002` 또는 `8000`도 사용 중이면 host port만 바꿔 실행합니다. 컨테이너 내부 통신은 그대로라서 학습/서빙 코드는 바꿀 필요가 없습니다.

```bash
MLFLOW_HOST_PORT=5003 API_HOST_PORT=8001 docker compose --profile continuous up -d
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

## Notebook

결과 조회용 notebook만 열 때 사용합니다.

```bash
uv sync --group notebook
uv run --group notebook jupyter lab results.ipynb
```
