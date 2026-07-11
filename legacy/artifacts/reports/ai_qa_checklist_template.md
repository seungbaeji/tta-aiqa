# AI QA 체크리스트

이 파일은 QA 판단 근거와 확인 상태를 한곳에 모으는 체크리스트입니다. 템플릿으로 쓸 때는 빈 항목을 채우고, 제출본으로 쓸 때는 근거 산출물과 담당자, 다음 조치를 함께 남깁니다.

| 판단 영역 | 근거 산출물 | 보고서에 남길 필드 |
| --- | --- | --- |
| 입력 변화 | `drift_report.md` | `heart_rate`, `oxygen_saturation`, shifted feature |
| 예측 변화 | `drift_report.md` | average score, `high_risk_rate` 변화 |
| 원인 후보 | `quality_issue_trace.md` | category, owner, audit_reference, next_action |
| 배포 판단 | `release_approval.md` | approved, failed_checks, failed check 관측값 |

## 근거 계보

최종 판단은 test 평가, validation 비교, 운영 current 관측을 분리해서 읽습니다. 아래 표는 이번 체크리스트가 어떤 데이터와 산출물에 근거하는지 보여줍니다.

| 판단 단계 | 근거 데이터 | 근거 산출물 | 판단 경계 |
| --- | --- | --- | --- |
| 평가 가능성 확인 | `vital_signs_evaluation_baseline.csv` | `chapter_01_quality_report.md` | 운영 입력 정상으로 확대하지 않음 |
| 모델 기준 평가 | `vital_signs_train.csv`, `vital_signs_test.csv` | `model_test_eval.json` | 선택된 모델과 threshold의 test 평가로 한정 |
| 데이터 조건 변화 비교 | `vital_signs_valid_baseline.csv`, `vital_signs_valid_degraded.csv` | `validation_degradation_comparison.json` | 운영 root cause 확정으로 쓰지 않음 |
| 운영 current 관측 | `serving_requests_current.csv`, `operational_current_events.jsonl` | `drift_report.md`, `quality_issue_trace.md` | 입력 구성 변화와 검증 실패를 후보 근거로 표현 |
| 배포 판단 | `release_regression_cases.csv` | `release_approval.md`, `ai_qa_checklist.md` | 조건부 보류와 재평가 조건을 확인 결과 path로 남김 |

근거 검토율: 0%
배포 준비 상태: ready
차단 상태: -

| 영역 | 상태 | 완료 | 확인 항목 | 근거 | QA 코멘트 | 담당 | 다음 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 데이터 품질 | unchecked | [ ] | 필수 컬럼(column) 존재 여부 확인 | - |  | - | - |
| 데이터 품질 | unchecked | [ ] | 결측값과 이상치 검토 | - |  | - | - |
| 데이터 품질 | unchecked | [ ] | 중복 행, 빈 컬럼, 상수 또는 거의 상수 컬럼 검토 | - |  | - | - |
| 데이터 품질 | unchecked | [ ] | 라벨(label) 허용값과 라벨 값 표준화 기준 확인 | - |  | - | - |
| 데이터 품질 | unchecked | [ ] | 관심 클래스 표본 수(Positive support) 충분성 확인 | - |  | - | - |
| 모델 품질 | unchecked | [ ] | 정밀도(Precision)와 재현율(Recall) 기준 충족 확인 | - |  | - | - |
| 모델 품질 | unchecked | [ ] | 혼동 행렬(Confusion Matrix)과 FP/FN 검토 | - |  | - | - |
| 모델 품질 | unchecked | [ ] | PR-AUC와 클래스(class) 불균형 영향 검토 | - |  | - | - |
| 모델 품질 | unchecked | [ ] | 임계값(threshold) 변경 영향 검토 | - |  | - | - |
| 서빙 품질 | unchecked | [ ] | API 계약(contract) 확인 | - |  | - | - |
| 서빙 품질 | unchecked | [ ] | 모델 버전(model_version) 일치 여부 확인 | - |  | - | - |
| 서빙 품질 | unchecked | [ ] | 임계값(threshold) 설정 일치 여부 확인 | - |  | - | - |
| 서빙 품질 | unchecked | [ ] | 오류 응답과 `request_id` 추적 가능성 확인 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | `request_id`, `trace_id` 로그 기록 확인 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | 점수(score)와 예측(prediction) 로그 기록 확인 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | 오류율(error rate)과 지연 시간(latency) 대시보드 확인 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | 검증 실패(validation failure) 추적 가능성 확인 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | 기준선(reference)과 현재(current) 비교 기간 확인 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | label 지연 시 proxy metric과 label 기반 재평가 조건 분리 | - |  | - | - |
| 운영 관측 | unchecked | [ ] | dashboard alert 또는 보고 trigger와 owner 지정 | - |  | - | - |
| 이상 징후 보고 | unchecked | [ ] | 증상 요약 | - |  | - | - |
| 이상 징후 보고 | unchecked | [ ] | 근거 자료 첨부 | - |  | - | - |
| 이상 징후 보고 | unchecked | [ ] | 원인 후보 분리 | - |  | - | - |
| 이상 징후 보고 | unchecked | [ ] | 다음 조치 담당과 확인 항목 지정 | - |  | - | - |
