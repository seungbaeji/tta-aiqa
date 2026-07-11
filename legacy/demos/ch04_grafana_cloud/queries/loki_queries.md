# Grafana Cloud Logs Queries

request_id로 단일 요청을 추적합니다.

```logql
{service="ai-quality-serving"} | json | request_id="anomaly-0004"
```

검증 실패(validation failure)가 발생한 요청을 찾습니다.

```logql
{service="ai-quality-serving"} | json | validation_failure="true"
```

예측(prediction) 분포가 특정 클래스(class)로 치우치는지 확인합니다.

```logql
{service="ai-quality-serving"} | json | prediction="high_risk"
```

trace_id로 같은 흐름에 속한 이벤트를 확인합니다.

```logql
{service="ai-quality-serving"} | json | trace_id="anomaly-trace-0001"
```
