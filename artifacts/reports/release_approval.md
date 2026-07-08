# 릴리스 판단 요약

승인 여부와 실패 기준만 먼저 확인하는 요약입니다. 상세 원인 후보는 `quality_issue_trace.md`에서 확인합니다.

- recommendation: conditional_hold
- approved: False
- failed_checks: recall, error_rate
- unresolved_risks: live_deployment
- re_evaluation_condition: failed_checks와 unresolved_risks가 해소되고 owner별 evidence가 같은 approval rule을 통과하면 재평가합니다.
- notes: 실패한 기준을 검토할 때까지 배포를 보류합니다.

## 기준별 결과

| check | observed | criterion | result |
| --- | --- | --- | --- |
| precision | 1.0000 | >= 0.6000 | pass |
| recall | 0.5926 | >= 0.6000 | fail |
| error_rate | 0.0667 | <= 0.0500 | fail |
| latency | 223.7500 | <= 250.0000 ms | pass |
| prepared_api_contract | True | local/prepared contract evidence is True | pass |

## 미해소 리스크

| area | status | evidence | owner | next_action |
| --- | --- | --- | --- | --- |
| live_deployment | unverified | No live /health, /predict, Pod readiness, model_version, or threshold evidence in the local course artifact. | Platform/MLOps | Collect live deployment smoke-test evidence before using deployment readiness as an approval basis. |
