# aiqa-observability

## 1. 책임

### 1-1. Telemetry contract

Prediction observation과 bounded-cardinality telemetry 계약을 소유합니다. Prometheus exposition, structured logging과 OpenTelemetry instrumentation은 adapter에서 구현합니다. Grafana dashboard API는 이 package의 책임이 아닙니다.
