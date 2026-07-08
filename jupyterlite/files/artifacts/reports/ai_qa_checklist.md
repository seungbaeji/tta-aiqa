# AI QA 체크리스트

최종 판단에 필요한 확인 항목만 모읍니다. 자세한 숫자와 근거 계보는 각 `근거` 파일에서 확인합니다.

- 근거 검토율: 100%
- 릴리스 준비 상태: blocked
- 차단 상태: fail, hold, unverified

| 영역 | 상태 | 완료 | 확인 항목 | 근거 | QA 코멘트 | 담당 | 다음 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 데이터 품질 | pass | [x] | 라벨 허용값과 표본 수 확인 | label_basis_check.md | invalid=0, missing=0, high_risk=37, low_risk=33 | QA Lead | release report에 label basis 유지 근거로 첨부 |
| 입력 변화 | fail | [x] | 입력 분포 변화 확인 | drift_report.md | heart_rate +10.4917, oxygen_saturation -1.4698 shift 확인 | Data Engineering | 데이터 수집 경로와 upstream feed 변경 여부 확인 |
| 모델 품질 | fail | [x] | 정밀도와 재현율 승인 기준 확인 | release_approval.md | failed_checks=recall, error_rate | ML Engineering | 평가 데이터와 threshold 영향 재검토 |
| 서빙 품질 | pass | [x] | 준비된 API 계약 증거 확인 | release_approval.md | prepared_api_contract=True, live evidence와 분리 | Platform/MLOps | live smoke evidence와 혼동하지 않도록 보고서에 한정 표현 |
| 서빙 품질 | unverified | [x] | live deployment evidence 확인 | release_approval.md | unresolved_risks=live_deployment | Platform/MLOps | /health, /predict, Pod readiness, model_version, threshold 증거 수집 |
| 운영 관측 | fail | [x] | 오류율과 검증 실패 확인 | quality_issue_trace.md | error_rate 기준 초과와 api_validation 후보 유지 | Client Integration | failed_field, client_id, source_system 기준으로 payload 변경 확인 |
| 최종 판단 | hold | [x] | 배포 승인 또는 보류 의견 | release_approval.md | recommendation=conditional_hold, approved=False | QA Lead | 실패 기준과 미검증 리스크 해소 후 재평가 |
