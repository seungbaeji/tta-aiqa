# AI QA 체크리스트

이 파일은 QA 판단 근거와 확인 상태를 한곳에 모으는 체크리스트입니다. 템플릿으로 쓸 때는 빈 항목을 채우고, 제출본으로 쓸 때는 근거 산출물과 담당자, 다음 조치를 함께 남깁니다.

| 판단 영역 | 근거 산출물 | 보고서에 남길 필드 |
| --- | --- | --- |
| 입력 변화 | `drift_report.md` | `heart_rate`, `oxygen_saturation`, shifted feature |
| 예측 변화 | `drift_report.md` | average score, `high_risk_rate` 변화 |
| 원인 후보 | `quality_issue_trace.md` | category, owner, audit_reference, next_action |
| 승인 판단 | `release_approval.md` | approved, failed_checks, failed check 관측값 |

## 근거 계보

근거 계보의 판단은 test 평가, validation 비교, 운영 current 관측을 분리해서 읽을 때 방어 가능합니다. 이 표는 이번 체크리스트가 어떤 데이터와 산출물에 근거하며, 각 근거를 어디까지 해석해야 하는지 보여줍니다.

| 판단 단계 | 근거 데이터 | 근거 산출물 | 판단 경계 |
| --- | --- | --- | --- |
| 평가 가능성 확인 | `vital_signs_evaluation_baseline.csv` | `chapter_01_quality_report.md` | 운영 입력 정상으로 확대하지 않음 |
| 모델 기준 평가 | `vital_signs_train.csv`, `vital_signs_test.csv` | `model_test_eval.json` | 선택된 모델과 threshold의 test 평가로 한정 |
| 데이터 조건 변화 비교 | `vital_signs_valid_baseline.csv`, `vital_signs_valid_degraded.csv` | `validation_degradation_comparison.json` | 운영 root cause 확정으로 쓰지 않음 |
| 운영 current 관측 | `serving_requests_current.csv`, `operational_current_events.jsonl` | `drift_report.md`, `quality_issue_trace.md` | 입력 구성 변화와 검증 실패를 후보 근거로 표현 |
| 릴리스 판단 | `release_regression_cases.csv` | `release_approval.md`, `ai_qa_checklist.md` | 조건부 보류와 재평가 조건을 evidence path로 남김 |

근거 검토율: 100%
릴리스 준비 상태: blocked
차단 상태: fail, hold, unverified

| 영역 | 상태 | 완료 | 확인 항목 | 근거 | QA 코멘트 | 담당 | 다음 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 데이터 품질 | pass | [x] | 라벨 허용값과 표본 수 확인 | label_basis_check.md | invalid=0, missing=0, high_risk=37, low_risk=33 | QA Lead | release report에 label basis 유지 근거로 첨부 |
| 입력 변화 | fail | [x] | 입력 분포 변화 확인 | drift_report.md | heart_rate +10.4917, oxygen_saturation -1.4698 shift 확인 | Data Engineering | 데이터 수집 경로와 upstream feed 변경 여부 확인 |
| 모델 품질 | fail | [x] | 정밀도와 재현율 승인 기준 확인 | release_approval.md | failed_checks=recall, error_rate | ML Engineering | 평가 데이터와 threshold 영향 재검토 |
| 서빙 품질 | pass | [x] | 준비된 API 계약 증거 확인 | release_approval.md | prepared_api_contract=True, live evidence와 분리 | Platform/MLOps | live smoke evidence와 혼동하지 않도록 보고서에 한정 표현 |
| 서빙 품질 | unverified | [x] | live deployment evidence 확인 | release_approval.md | unresolved_risks=live_deployment | Platform/MLOps | /health, /predict, Pod readiness, model_version, threshold 증거 수집 |
| 운영 관측 | fail | [x] | 오류율과 검증 실패 확인 | quality_issue_trace.md | error_rate 기준 초과와 api_validation 후보 유지 | Client Integration | failed_field, client_id, source_system 기준으로 payload 변경 확인 |
| 최종 판단 | hold | [x] | 배포 승인 또는 보류 의견 | release_approval.md | recommendation=conditional_hold, approved=False | QA Lead | 실패 기준과 미검증 리스크 해소 후 재평가 |
