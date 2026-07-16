# aiqa-observability

## 1. 책임

### 1-1. Platform SDK

`aiqa-observability`는 모든 AIQA Python process가 사용하는 platform SDK입니다. 실행 단위의 `request_id`, `run_id`, `scenario`와 operation context를 `ContextVar`로 관리하고, JSON structured log, W3C trace, 선택적 Prometheus metric registry를 같은 context로 연결합니다.

### 1-2. 소유하지 않는 것

모델 예측 event 이름, metric 이름·label·bucket, traffic scenario, dashboard query는 각 app의 책임입니다. 예를 들어 Risk API의 metric 정책은 `configs/serving/api.yaml`에 있고, dashboard import는 `apps/grafana-dashboard-importer`가 담당합니다. Grafana, Loki, Tempo와 Prometheus server의 배포도 이 package의 책임이 아닙니다.

### 1-3. Module boundaries

`domain`은 telemetry attributes, execution context inheritance, events, metric declarations, policy와 resource identity만 소유한다. `adapters.logging`, `adapters.prometheus`, `adapters.opentelemetry`, `adapters.fastapi`, `adapters.config`은 각각 structured log, bounded metric, tracing/OTLP, framework bridge, YAML/Pydantic boundary를 소유한다. Public `Telemetry` facade는 이 기술들을 조립해 app이 context variable이나 Prometheus client를 직접 다루지 않도록 한다.

## 2. 사용 방식

### 2-1. Process composition

각 app의 composition root는 `create_telemetry()`를 한 번 호출합니다. CLI와 batch job은 `run_scope()`로 root span과 run context를 만들고, FastAPI app은 자신의 middleware에서 `request_scope()`를 사용합니다. HTTP middleware의 route, request validation과 business policy는 app에 남기며, `instrument_fastapi()`와 `telemetry_lifespan()`만 framework bridge로 제공합니다.

### 2-2. Signal 경계

- `event()`는 현재 context를 JSON log와 active span event로 기록합니다.
- `operation_scope()`는 request 또는 run 아래의 child span을 만듭니다.
- `outbound_trace_headers()`는 app-owned HTTP adapter가 다음 process에 trace context를 전달할 때 사용합니다.
- `MetricSpec`은 app이 선언한 bounded metric만 등록합니다. `request_id`, `run_id`, `trace_id`, `span_id`는 metric label로 허용하지 않습니다.

## 3. 설정

### 3-1. 공통 정책

`configs/observability/telemetry.yaml`은 모든 process가 공유하는 최소 policy만 둡니다.

```yaml
schema_version: 2
service_namespace: tta-aiqa
logging:
  level: INFO
```

OTLP endpoint, environment, config path는 app별 `pydantic-settings` runtime setting으로 주입합니다. Grafana Cloud credential은 app이 아니라 Alloy에만 전달합니다.
