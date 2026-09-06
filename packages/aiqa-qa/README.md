# aiqa-qa

## 1. 책임

### 1-1. Release policy

Release policy는 baseline, Candidate A, Candidate B의 profile identity와 Recall, uncertainty, Precision, PR-AUC, false-negative guardrail을 함께 소유합니다. 각 check 이름은 domain enum으로 고정되며, 승인 여부는 모든 guardrail 결과와 일치해야 합니다.

### 1-2. Application and adapters

`evaluate_candidate_releases`는 policy가 지정한 baseline과 candidate 순서를 검증한 뒤 두 후보를 독립적으로 평가하는 함수형 use case다. YAML과 JSON evidence는 Pydantic DTO adapter에서 검증하고, application과 caller에는 immutable domain policy와 result만 전달한다.
