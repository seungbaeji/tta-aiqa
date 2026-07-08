# Grafana Cloud Metrics Queries

요청 수를 확인합니다.

```promql
ai_quality_request_total
```

오류 비율을 확인합니다.

```promql
ai_quality_error_total / ai_quality_request_total
```

평균 latency를 확인합니다.

```promql
ai_quality_latency_average_ms
```

Positive class 예측 비율을 확인합니다.

```promql
ai_quality_high_risk_rate
```

검증 실패를 제외한 Positive class 예측 비율을 확인합니다.

```promql
ai_quality_valid_high_risk_rate
```

평균 score 변화를 확인합니다.

```promql
ai_quality_score_average
```

검증 실패를 제외한 평균 score 변화를 확인합니다.

```promql
ai_quality_valid_score_average
```
