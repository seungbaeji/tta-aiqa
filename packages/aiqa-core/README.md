# aiqa-core

## 1. 책임

### 1-1. Shared kernel

Feature contract와 model role처럼 bounded context 사이에서 의미가 변하지 않는 domain value만 제공합니다. Versioned feature YAML을 domain value로 변환하는 adapter를 포함하며 업무 workflow는 소유하지 않습니다.
