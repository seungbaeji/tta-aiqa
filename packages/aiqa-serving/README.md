# aiqa-serving

## 1. 책임

### 1-1. Online prediction

Model identity, prediction request/result와 event를 소유합니다. `PredictRisk` use case는 scorer와 event recorder port에만 의존하고 local sklearn과 KServe HTTP 구현은 교체 가능한 adapter로 제공합니다.
