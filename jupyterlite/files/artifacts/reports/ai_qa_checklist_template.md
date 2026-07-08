# AI QA 체크리스트

최종 판단에 필요한 확인 항목만 모읍니다. 자세한 숫자와 근거 계보는 각 `근거` 파일에서 확인합니다.

- 근거 검토율: 0%
- 릴리스 준비 상태: ready
- 차단 상태: -

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
