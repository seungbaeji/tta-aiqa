# Deployment Decision Report

## Decision Summary

| recommendation | approved | failed_checks | unresolved_risks | re_evaluation_condition |
| --- | --- | --- | --- | --- |
| conditional_hold | False | recall, error_rate | live_deployment | failed_checks와 unresolved_risks가 해소되고 owner별 확인 결과가 같은 배포 기준을 만족하면 재평가합니다. |

| approved | failed_checks | notes |
| --- | --- | --- |
| False | recall, error_rate | 실패한 기준을 검토할 때까지 배포를 보류합니다. |

| check | observed | criterion | result |
| --- | --- | --- | --- |
| precision | 1.0000 | >= 0.6000 | pass |
| recall | 0.5926 | >= 0.6000 | fail |
| error_rate | 0.0667 | <= 0.0500 | fail |
| latency | 223.7500 | <= 250.0000 ms | pass |
| prepared_api_contract | True | local/prepared contract check is True | pass |

## Unresolved Deployment Checks

| area | status | 확인 결과 | owner | next_action |
| --- | --- | --- | --- | --- |
| live_deployment | unverified | No live /health, /predict, Pod readiness, model_version, or threshold check in the local course artifact. | Platform/MLOps | Collect live deployment smoke-test result before using deployment readiness as an approval basis. |

## Deployment Risk Tradeoff

| decision | company_risk | 확인 결과 | missing_check | owner | next_action |
| --- | --- | --- | --- | --- | --- |
| approve_now | 기준 미달 지표와 미검증 live deployment 상태가 운영에 반영되어 FP/FN, 오류 요청, 추적 공백이 증가할 수 있습니다. | failed_checks=recall, error_rate; unresolved_risks=live_deployment | 실패 기준 재측정, 검증 실패 원인 확인, live /health, /predict, Pod readiness, 응답 model_version/threshold | QA Lead | 승인하지 않고 owner별 확인 결과를 같은 배포 기준으로 다시 검토합니다. |
| conditional_hold | 배포 지연과 현재 운영 버전 유지 부담이 생기므로 보류 사유와 해제 조건을 명확히 공유해야 합니다. | latency와 prepared_api_contract는 통과했지만 recall, error_rate 기준과 live_deployment 리스크가 남아 있습니다. | owner별 next action 완료 결과와 같은 배포 기준 재평가 | Deployment Owner | Data Engineering, ML Engineering, Client Integration, Platform/MLOps 확인 결과를 모아 같은 기준으로 재평가합니다. |
