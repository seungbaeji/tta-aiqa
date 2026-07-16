# aiqa-data

## 1. 책임

### 1-1. Data bounded context

PhysioNet raw record, patient feature aggregation, typed source-integrity evidence, dataset role, split와 revision lineage를 소유합니다. Application use case는 repository와 split port에 의존하고 YAML, CSV, checksum, download, archive와 sklearn 처리는 adapter에 격리합니다.
