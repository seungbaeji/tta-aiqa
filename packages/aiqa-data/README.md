# aiqa-data

## 1. 책임

### 1-1. Data bounded context

PhysioNet record, patient feature aggregation, dataset role, split와 revision lineage를 소유합니다. Application use case는 repository와 split port에 의존하고 YAML, CSV, sklearn과 archive 처리는 adapter에 격리합니다.
