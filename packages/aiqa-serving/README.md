# aiqa-serving

## 1. 책임

### 1-1. Online prediction

Model identity, typed prediction request/result와 prediction event를 domain value로 소유합니다. application은 ordered internal feature tuple만 받으며 canonical contract에 맞춰 검증한 뒤 scoring과 event recording을 orchestration한다.

### 1-2. Scoring adapters

`RiskScorer`는 local joblib bundle과 KServe V2 HTTP 구현을 교체 가능하게 분리한다. local bundle은 process startup에 feature-contract digest와 metadata를 검증해 한 번만 로드하며, public API reload는 제공하지 않는다. KServe JSON response도 Pydantic DTO로 검증한 뒤 model identity와 positive-class score를 확인한다.
