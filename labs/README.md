# Labs

## 1. 진행 순서

### 1-1. 1일차

1. [ch01 Data Quality](ch01-data-quality/README.md): 수동 EDA 후 GE 자동 검증
2. [ch02 Model Quality](ch02-model-quality/README.md): 세 모델의 prepared evidence와 MLflow 비교

### 1-2. 2일차

3. [ch03 Serving](ch03-serving/README.md): Compose Risk API와 Kubernetes adapter 확인
4. [ch04 Observability](ch04-observability/README.md): Alloy, Grafana Cloud와 dashboard 연결
5. [ch05 Release Decision](ch05-release-decision/README.md): Candidate A HOLD, Candidate B APPROVE와 rollback

각 장의 README에서 runtime 명령을 먼저 수행하고 Notebook을 위에서 아래로 실행합니다. 모델 개발 탐색은 `reference/evidence/model/revisions/v2/` 아래의 development benchmark와 feature diagnostics에 내부 증거로 보존합니다. 수강생은 feature engineering이나 threshold tuning을 다시 수행하지 않고 준비된 evidence를 읽어 데이터·모델·운영 품질을 연결합니다.
