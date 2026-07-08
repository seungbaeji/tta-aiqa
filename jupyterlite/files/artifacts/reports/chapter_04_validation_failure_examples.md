# Chapter 04 Validation Failure Examples

이 파일은 4장 운영 관측 보고서에서 검증 실패 owner와 next action을 지정하기 위한 prepared evidence입니다.

| request_id | client_id | source_system | failed_field | error_category | error_detail | owner | next_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| current-0000 | partner-feed-v2 | upstream-partner-feed | oxygen_saturation | schema_validation | oxygen_saturation is outside accepted serving range | Client Integration | oxygen_saturation 입력 생성 로직과 API schema 변경 이력을 확인합니다. |
| current-0017 | partner-feed-v2 | upstream-partner-feed | heart_rate | schema_validation | heart_rate is missing from client payload | Client Integration | heart_rate 입력 생성 로직과 API schema 변경 이력을 확인합니다. |
| current-0034 | partner-feed-v2 | upstream-partner-feed | oxygen_saturation | schema_validation | oxygen_saturation is outside accepted serving range | Client Integration | oxygen_saturation 입력 생성 로직과 API schema 변경 이력을 확인합니다. |
| current-0051 | partner-feed-v2 | upstream-partner-feed | heart_rate | schema_validation | heart_rate is missing from client payload | Client Integration | heart_rate 입력 생성 로직과 API schema 변경 이력을 확인합니다. |
| current-0068 | partner-feed-v2 | upstream-partner-feed | oxygen_saturation | schema_validation | oxygen_saturation is outside accepted serving range | Client Integration | oxygen_saturation 입력 생성 로직과 API schema 변경 이력을 확인합니다. |
