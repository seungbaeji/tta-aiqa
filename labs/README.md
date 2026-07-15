# Labs

## 1. 시작 전 확인

### 1-1. 공통 실행 경계

모든 command는 제공 VM의 VS Code Remote SSH terminal에서 실행합니다. host OS의
terminal에서 repository를 따로 실행하지 않습니다.

```bash
uv sync --all-packages --group notebook
uv run python scripts/setup_course.py
```

이후 `git status --short`가 비어 있어야 합니다. data 재현 결과는 local DVC
workspace에, V2 canonical evidence는 `docs/reference/evidence/`에 분리되어 있습니다.

### 1-2. 공통 완료 증거

모든 수강생은 역할과 무관하게 다음 다섯 가지를 설명하고 확인합니다.

1. 원본에서 patient-level data와 GE validation이 어떻게 생성되는가
2. Candidate A HOLD와 Candidate B APPROVE를 만든 release guardrail은 무엇인가
3. Risk API의 정상 요청, contract violation, request ID와 model identity는 무엇인가
4. Grafana dashboard에서 baseline과 Candidate B model version을 어떻게 구분하는가
5. release manifest, immutable model path와 rollback overlay가 어떻게 연결되는가

### 1-3. 역할별 관점

| 역할 | 공통 흐름에서 추가로 확인할 질문 |
| --- | --- |
| QA | 어떤 data/API/release contract가 실패이며 owner와 재평가 조건은 무엇인가 |
| 개발자 | request/response, 422 validation, request ID와 structured telemetry는 어떻게 연결되는가 |
| ML Engineer | split, feature contract, profile, threshold와 guardrail은 어느 시점에 동결되는가 |
| DevOps | Secret, immutable model path, Kustomize desired state와 rollback은 무엇을 바꾸는가 |
| MLOps | Git, DVC, MLflow, bundle digest, release manifest의 책임은 어떻게 다른가 |

## 2. 진행 순서

### 2-1. 1일차

1. [ch01 Data Quality](ch01-data-quality/README.md): 수동 EDA 후 GE 자동 검증
2. [ch02 Model Quality](ch02-model-quality/README.md): 세 모델의 prepared evidence와 MLflow 비교

### 2-2. 2일차

3. [ch03 Serving](ch03-serving/README.md): Compose Risk API와 Kubernetes adapter 확인
4. [ch04 Observability](ch04-observability/README.md): Alloy, Grafana Cloud와 dashboard 연결
5. [ch05 Release Decision](ch05-release-decision/README.md): Candidate A HOLD, Candidate B APPROVE와 rollback

각 장의 README에서 runtime 명령을 먼저 수행하고 Notebook을 위에서 아래로 실행합니다. 모델 개발 탐색은 `docs/reference/evidence/model/revisions/v2/` 아래의 development benchmark와 feature diagnostics에 내부 증거로 보존합니다. 수강생은 feature engineering이나 threshold tuning을 다시 수행하지 않고 준비된 evidence를 읽어 데이터·모델·운영 품질을 연결합니다.

## 3. 환경 경계

### 3-1. 강사와 수강생 책임

강사는 VM baseline, Risk API endpoint, Kubernetes/Argo CD 접근 정책을 제공합니다.
수강생은 자신의 Grafana Cloud credential로 Alloy secret과 dashboard를 만들고, 각
chapter의 evidence를 확인합니다. candidate overlay sync와 rollback은 강사가
안내한 GitOps 절차 안에서만 수행합니다.
