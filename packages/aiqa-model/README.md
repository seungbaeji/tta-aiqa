# aiqa-model

## 1. 책임

### 1-1. Model lifecycle

Model profile, metric과 benchmark result를 domain value로 관리합니다. Application use case는 `ModelBenchmark` port만 호출하며 sklearn training, MLflow, evidence serialization과 bundle filesystem은 adapter가 담당합니다.
