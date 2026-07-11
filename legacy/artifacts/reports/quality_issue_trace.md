# Quality Issue Trace

| category | evidence | owner | audit_reference | next_action |
| --- | --- | --- | --- | --- |
| input_case_mix_shift | shifted_features=heart_rate, oxygen_saturation | Data Engineering | artifacts/reports/drift_report.md#input-distribution | 최근 입력 출처와 전처리 변경을 확인합니다. |
| prediction_shift | high_risk_rate_delta=0.2417 | ML Engineering | artifacts/reports/drift_report.md#score-and-prediction-distribution | 점수 분포와 임계값 설정을 비교합니다. |
| api_validation | error_rate_delta=0.0667 | Client Integration | request_id=current-0000, client_id=partner-feed-v2, source_system=upstream-partner-feed, failed_field=oxygen_saturation | 검증 실패 예시에서 failed_field, client_id, source_system을 확인하고 Client Integration owner에게 전달합니다. |
| service_latency | latency_delta_ms=120.0 | Platform/MLOps | artifacts/grafana/ai_quality_overview_dashboard.json#average-latency | 서비스 부하, 의존성 지연, Pod 상태를 확인합니다. |
