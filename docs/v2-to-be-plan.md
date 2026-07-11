# TTA AIQA V2 TO-BE Plan

이 문서는 `tta-aiqa` V2의 교육 시나리오, monorepo 구조, 데이터와 모델 계보, 실행 환경, 수강생 동선과 구현 순서를 정의하는 단일 기획 문서다. 기존 package 분리 계획과 monorepo 초안을 이 문서로 통합한다.

## 1. 목표

### 1-1. V2 목표

기존 2일 교육과정의 주제와 순서는 유지한다. Repository 내부 구현을 실제 데이터, 실제 baseline/candidate model, 실제 API, GitOps 배포와 운영 관측 신호가 하나의 품질 판단 사건으로 이어지도록 재구성한다.

```text
기준 데이터 품질 확인
  -> 데이터 검증 자동화
  -> baseline/candidate 모델 평가
  -> 데이터 revision과 MLflow run 연결
  -> baseline 모델 serving과 candidate 배포 확인
  -> 운영 traffic과 telemetry 확인
  -> 품질 이상 원인 후보와 대응 판단
```

### 1-2. 변경 원칙

- 공개 커리큘럼은 기존 2일 14교시 구성을 유지한다.
- DVC만 기존 모델 실험 관리 구간에 추가한다.
- 수강생은 모델 개발자가 아니라 AI 서비스 품질/운영 담당자 역할을 맡는다.
- `apps/`는 독립 실행 process, `packages/`는 재사용 로직을 소유한다.
- 교육용 수치는 하드코딩하지 않고 고정된 데이터와 코드에서 계산한다.
- Clean Architecture와 DDD dependency 규칙을 자동 test로 강제한다.
- Use case는 TDD로 구현하고 교육 사건은 BDD acceptance scenario로 고정한다.
- 비용이 발생하는 managed service를 필수 경로로 사용하지 않는다.
- `legacy/`는 archive이며 새 코드에서 import하지 않는다.

### 1-3. 범위 밖

- VM 생성, clone, DNS, network와 monitoring backend 운영은 `mrml-infra` 책임이다.
- Proxmox 구조와 사용법은 수강생 교육 내용에 포함하지 않는다.
- 실제 학생 계정, IP, domain inventory와 credential은 두 교육 repository에 저장하지 않는다.
- JupyterLite는 V2 필수 범위에 포함하지 않는다.
- DVC remote와 유료 object storage는 사용하지 않는다.

## 2. 기준 문서와 Repository 경계

### 2-1. 교육 기준

교육 목표와 시나리오는 `ttamlops-2607/docs/00_overview`를 기준으로 한다.

- `course.md`: 수강생 역할과 학습 목표
- `scenario.md`: 후보 모델 배포 판단 사건
- `dataset.md`: 데이터 역할과 lineage
- `levels.md`: 2일 운영 순서와 Core/Lab/Demo 구분
- `syllabus.md`: 장별 상세 내용
- `tool-evidence-map.md`: 도구와 판단 근거 연결
- `repository-boundary.md`: 교재와 실습 코드의 역할
- `docs/img/curriculum.png`: 기존 2일 14교시 커리큘럼

### 2-2. 두 Repository 역할

```text
ttamlops-2607
  교재, 슬라이드, 기존 커리큘럼, 판단 기준, 수강생 설명

tta-aiqa
  apps, packages, labs, DVC pipeline, models, deployment assets, 실행 검증
```

교재는 무엇을 확인하고 어디까지 판단할 수 있는지 설명한다. 실습 repository는 같은 판단 근거를 실제로 재현한다.

### 2-3. Legacy 정책

- `legacy/` 파일을 새 app과 package가 import하지 않는다.
- 기존 labs, demos, package, artifact를 일괄 복원하지 않는다.
- 필요한 규칙, test case, manifest와 dashboard 구성만 새 구조로 다시 구현한다.
- `legacy/domains.csv`는 과거 환경 inventory 참고 자료로만 사용한다.
- 중복 Notebook, JupyterLite mirror, 생성 HTML과 과거 runtime artifact는 기본 이관 대상이 아니다.

## 3. 교육 시나리오

### 3-1. 공통 사건

생체신호 기반 위험 알림 API는 baseline 모델로 운영 중이다. 새 candidate 모델이 MLflow에 기록되었고, 운영에서 `high_risk` prediction 비율과 validation failure가 증가한다.

수강생은 다음 질문에 답한다.

```text
이 candidate 모델을 배포해도 되는가?
보류한다면 어떤 근거와 재평가 조건이 필요한가?
배포 후 문제가 확인되면 어떤 기준으로 되돌릴 것인가?
```

### 3-2. 판단 근거

- 기준 데이터의 column, null, range와 label 분포
- Great Expectations baseline/degraded validation 결과
- baseline/candidate Precision, Recall, F1, FP/FN과 threshold
- DVC data revision과 MLflow dataset/run lineage
- container, API contract와 model metadata
- Kubernetes desired/live state와 Argo CD sync 결과
- endpoint response, model version, request ID와 trace ID
- error rate, latency, score와 prediction distribution
- Grafana dashboard와 상세 log/trace

### 3-3. 결론 표현

단일 metric, API 성공 또는 Argo CD sync만으로 배포를 승인하지 않는다. 최종 판단에는 다음을 포함한다.

- 현재 판단
- 사용한 evidence와 audit reference
- 확인하지 못한 범위
- 남은 risk
- owner와 next action
- rollback trigger
- 재평가 조건

## 4. TO-BE 폴더 구조

### 4-1. 전체 구조

```text
tta-aiqa/
├── apps/
│   ├── data-quality-pipeline/
│   ├── model-trainer/
│   ├── risk-api/
│   └── traffic-generator/
├── packages/
│   ├── aiqa-core/
│   ├── aiqa-data/
│   ├── aiqa-model/
│   ├── aiqa-serving/
│   ├── aiqa-observability/
│   └── aiqa-qa/
├── labs/
│   ├── README.md
│   ├── ch01-data-quality/
│   ├── ch02-model-quality/
│   ├── ch03-serving/
│   ├── ch04-observability/
│   └── ch05-release-decision/
├── data/
│   ├── README.md
│   ├── raw/
│   ├── snapshots/
│   ├── processed/
│   ├── scenarios/
│   └── quarantine/
├── artifacts/
│   ├── data-quality/
│   ├── models/
│   ├── mlflow/
│   ├── events/
│   ├── metrics/
│   ├── traces/
│   └── reports/
├── deploy/
│   ├── compose/simple-mlops/
│   ├── kubernetes/
│   └── gitops/
├── scripts/
├── tests/
│   ├── architecture/
│   ├── bdd/
│   │   ├── features/
│   │   └── steps/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── adr/
│   └── v2-to-be-plan.md
├── legacy/
├── .dvc/
├── dvc.yaml
├── dvc.lock
├── params.yaml
├── pyproject.toml
├── uv.lock
└── README.md
```

### 4-2. Simple MLOps 이름

`simple-mlops`는 Python app 이름이 아니라 전체 실행 stack의 이름으로 사용한다.

```text
deploy/compose/simple-mlops/
├── compose.yaml
├── alloy.example.alloy
├── .env.example
└── README.md
```

## 5. Apps

### 5-1. Data Quality Pipeline

`apps/data-quality-pipeline`은 데이터 snapshot, split, scenario 생성과 Great Expectations 검증을 실행한다.

```text
apps/data-quality-pipeline/
├── src/data_quality_pipeline/
│   ├── main.py
│   ├── pipeline.py
│   └── settings.py
├── gx/
│   ├── great_expectations.yml
│   ├── expectations/
│   └── checkpoints/
├── tests/
├── pyproject.toml
└── README.md
```

제공 command:

```text
prepare    raw에서 snapshot, split과 scenario 생성
validate   GE expectation과 checkpoint 실행
```

### 5-2. Model Trainer

`apps/model-trainer`는 baseline/candidate model을 실제로 생성하고 MLflow에 기록한다.

```text
apps/model-trainer/
├── src/model_trainer/
│   ├── main.py
│   ├── profiles.py
│   └── settings.py
├── tests/
├── Dockerfile
└── pyproject.toml
```

강사 및 개발자용 `bootstrap` command는 두 model bundle을 만들고 baseline을 초기 deployed model로 publish한다.

### 5-3. Risk API

`apps/risk-api`는 deployed model을 읽어 온라인 추론을 제공한다.

```text
apps/risk-api/src/risk_api/
├── main.py
├── settings.py
├── dependencies.py
├── api/
│   ├── schemas.py
│   ├── middleware.py
│   ├── exception_handlers.py
│   └── routes/
│       ├── prediction.py
│       ├── operations.py
│       └── diagnostics.py
└── runtime/
    ├── model_provider.py
    └── event_recorder.py
```

Endpoint 계약:

```text
GET  /health
POST /predict
POST /predict-batch
POST /reload
GET  /metrics
GET  /events
GET  /docs
```

### 5-4. Traffic Generator

`apps/traffic-generator`는 API와 독립된 운영 traffic simulator다.

```text
baseline                평상시 입력과 기준 prediction 분포
current-shift           입력 구성 변화와 high-risk rate 증가
validation-failure      null과 range 오류 요청
candidate-regression    candidate guardrail 확인 요청
```

Traffic은 고정 seed로 재현하고 client response와 server prediction event를 서로 다른 artifact로 관리한다.

## 6. Packages

### 6-1. AIQA Core

- feature, label과 threshold 계약
- cross-context identifier와 model role
- package 간 공유하는 순수 상수

`aiqa-core`는 다른 AIQA package를 의존하지 않는다.
Model metadata, prediction result와 prediction event는 각각의 bounded context가 소유하며 core로 이동하지 않는다.

### 6-2. AIQA Data

- column과 label 표준화
- type 변환과 valid/quarantine 분리
- temporal snapshot 생성
- stratified deterministic split
- degraded와 operational scenario 생성
- dataset manifest와 hash 생성

Model 학습과 prediction event 생성은 포함하지 않는다.

### 6-3. AIQA Model

- sklearn pipeline 생성
- 학습, scoring과 평가
- metric과 confusion matrix 계산
- threshold 평가
- model과 metadata 저장 및 로딩
- MLflow dataset/run/model logging
- baseline/candidate 비교 결과 생성

CLI, sleep loop와 환경 변수는 포함하지 않는다.

### 6-4. AIQA Serving

- HTTP framework와 독립된 prediction use case
- scoring model protocol
- event sink protocol
- score, threshold와 label 결정
- prediction result 계약

FastAPI route와 Pydantic HTTP schema는 app이 소유한다.

### 6-5. AIQA Observability

- structured prediction event
- JSONL event store
- Prometheus metric rendering
- baseline/current distribution 비교
- OTLP trace payload와 전송

Grafana credential, URL과 Alloy runtime config는 deployment 환경에서 주입한다.

### 6-6. AIQA QA

- data/model/deployment/operation evidence의 context-neutral summary
- evidence reference와 quality issue
- approval, conditional hold와 rollback policy
- `ReleaseDecision` 생성 use case
- owner, next action과 reevaluation condition 계약

`aiqa-qa`는 다른 bounded context의 entity를 직접 import하지 않는다. App 또는 Lab의 anti-corruption mapping을 통해 context별 output을 QA evidence DTO로 변환한다. 별도 `quality-gate` app은 우선 만들지 않고 5장 Lab과 BDD acceptance test가 package use case를 호출한다.

### 6-7. Import 방향

```text
                         aiqa-core
          ↑          ↑          ↑          ↑          ↑
     aiqa-data  aiqa-model  aiqa-serving  aiqa-observability  aiqa-qa
          ↑          ↑          ↑          ↑          ↑
          └──────── app composition roots and Labs ────┘
```

각 bounded context package는 원칙적으로 `aiqa-core`만 의존한다. Context 간 변환과 조립은 app composition root 또는 Lab adapter에서 수행한다. Package는 app을 import하지 않고 app 간 Python import도 허용하지 않는다.

| Composition Root | 조립하는 Context |
| --- | --- |
| Data Quality Pipeline | Data Quality |
| Model Trainer | Data Quality, Model Lifecycle |
| Risk API | Model Lifecycle, Serving, Observability |
| Traffic Generator | Shared Kernel과 HTTP client adapter |
| Release Decision Lab | Data Quality, Model Lifecycle, Observability, Release Assurance |

## 7. Architecture와 Test 전략

### 7-1. 필수 Engineering 원칙

V2 구현은 Clean Architecture, Domain-Driven Design과 Test-Driven Development를 기본 개발 원칙으로 사용한다. Behavior-Driven Development는 교육 시나리오와 end-to-end 인수 조건에 적용한다.

- Domain은 framework, filesystem, network와 vendor SDK를 모른다.
- Dependency는 바깥 layer에서 안쪽 layer로만 향한다.
- Business 용어와 invariant는 bounded context가 소유한다.
- App은 use case를 조립하는 composition root와 delivery adapter를 담당한다.
- 모든 behavior 변경은 실패하는 test 또는 BDD scenario에서 시작한다.
- Architecture 규칙은 문서에만 두지 않고 자동 test로 검증한다.

### 7-2. Bounded Context

| Bounded Context | Package | 핵심 책임 |
| --- | --- | --- |
| Shared Kernel | `aiqa-core` | 최소 공통 value와 cross-context identifier |
| Data Quality | `aiqa-data` | dataset snapshot, role, split, validation input과 lineage |
| Model Lifecycle | `aiqa-model` | training, evaluation, candidate와 model publication |
| Serving | `aiqa-serving` | prediction use case, scoring contract와 result |
| Observability | `aiqa-observability` | prediction event, metric, trace와 quality signal |
| Release Assurance | `aiqa-qa` | evidence, approval policy와 release decision |

`aiqa-core`를 공용 잡동사니 package로 사용하지 않는다. 둘 이상의 context가 실제로 공유하고 의미가 안정된 value만 Shared Kernel로 이동한다.

### 7-3. Ubiquitous Language

Code, test, artifact와 교재에서 다음 용어를 같은 의미로 사용한다.

```text
DatasetSnapshot
DatasetRole
DataRevision
ValidationResult
ModelProfile
ModelRole
ModelCandidate
PublishedModel
PredictionRequest
PredictionResult
PredictionEvent
EvidenceReference
QualityIssue
ReleaseDecision
```

`baseline`, `candidate`, `deployed`, `label`, `score`, `threshold`, `prediction`을 서로 바꾸어 쓰지 않는다. 용어 의미가 바뀌는 결정은 `docs/adr/`에 기록한다.

### 7-4. Package 내부 구조

각 package는 필요한 범위에서 다음 구조를 따른다.

```text
packages/<package>/src/<module>/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   └── services.py
├── application/
│   ├── commands.py
│   ├── queries.py
│   └── use_cases.py
├── ports/
│   ├── repositories.py
│   └── services.py
├── adapters/
│   ├── repositories.py
│   └── services.py
└── __init__.py
```

모든 package에 빈 layer를 기계적으로 만들지는 않는다. Domain invariant, use case, port 또는 adapter가 실제로 존재할 때만 해당 module을 추가한다.

Package 내부의 기술 구현 계층명은 `adapters`로 통일한다. Adapter는 application이 정의한 port를 구현하며 filesystem, database, HTTP client와 vendor SDK 같은 외부 기술 세부사항을 캡슐화한다.

### 7-5. Layer 의존 규칙

```text
domain
  외부 layer 의존 없음

application
  domain과 port 의존

ports
  Protocol과 domain type 정의

adapters
  port 구현, vendor SDK와 filesystem/network 사용

app
  settings, adapter와 use case 조립
```

Pandas DataFrame, FastAPI model, MLflow object, Great Expectations object와 HTTP response를 domain 경계 안으로 전달하지 않는다. Boundary에서는 domain value 또는 명시적인 DTO로 변환한다.

### 7-6. App Composition Root

App은 다른 app을 import하지 않는다. `main.py` 또는 `dependencies.py`에서 concrete adapter를 생성하고 use case의 port에 주입한다.

```text
FastAPI route / CLI
  -> input DTO 변환
  -> application use case
  -> port
  -> outbound adapter
  -> output DTO 변환
```

Dependency injection framework를 필수로 도입하지 않고 constructor와 factory 기반의 명시적 wiring을 우선한다.

### 7-7. Architecture Test

`tests/architecture`에서 다음 규칙을 자동 검증한다.

- domain module이 FastAPI, Pandas, MLflow, GE, requests와 filesystem adapter를 import하지 않음
- package가 `apps.*`를 import하지 않음
- app이 다른 app을 import하지 않음
- adapters가 아닌 layer에서 vendor SDK를 import하지 않음
- package public API가 app runtime path에 의존하지 않음
- bounded context 간 허용된 dependency만 존재함

초기에는 Python AST 기반 test로 시작하고 규칙이 복잡해질 때 import boundary 전용 도구 도입을 검토한다.

### 7-8. TDD Workflow

모든 use case와 defect 수정은 Red-Green-Refactor 순서로 진행한다.

```text
1. Domain behavior 또는 acceptance condition을 test로 표현
2. 실패를 확인
3. behavior를 통과하는 최소 구현
4. 전체 관련 test 통과 확인
5. naming, duplication과 dependency를 refactor
6. architecture test와 상위 scenario 재실행
```

Mock을 기본값으로 사용하지 않는다. Domain unit test에는 실제 value object를 사용하고 외부 경계에는 작은 fake adapter를 우선한다. Network, clock, UUID와 random은 port 또는 주입 가능한 dependency로 제어한다.

### 7-9. Test Pyramid

| Test 수준 | 위치 | 대상 |
| --- | --- | --- |
| Domain unit | 각 package `tests/unit` | invariant, value object와 domain service |
| Application unit | 각 package `tests/unit` | use case와 fake port interaction |
| Contract | 각 package `tests/contract` | port를 구현한 adapter 공통 계약 |
| Integration | package/app `tests/integration` | Pandas, GE, MLflow, filesystem, FastAPI adapter |
| Architecture | root `tests/architecture` | dependency와 layer 규칙 |
| BDD acceptance | root `tests/bdd` | 교육 사건과 사용자 관점 behavior |
| End-to-End | root `tests/e2e` | DVC, app, Compose, k3s와 telemetry 흐름 |

Unit test는 작고 빠르며 network와 Docker 없이 실행되어야 한다. Full source CSV 대신 최소 synthetic fixture를 사용하고 데이터 전체 재현은 integration/e2e로 제한한다.

### 7-10. BDD 적용 범위

BDD는 모든 함수 test를 Gherkin으로 바꾸는 방법이 아니다. 여러 bounded context와 app이 연결되는 교육 시나리오의 인수 조건에만 사용한다.

`pytest-bdd`를 pytest test stack에 통합하고 feature narrative는 한국어로 작성하되 `Given`, `When`, `Then` keyword와 domain term은 일관되게 유지한다.

```text
tests/bdd/
├── features/
│   ├── data_quality_gate.feature
│   ├── candidate_evaluation.feature
│   ├── baseline_serving.feature
│   ├── operational_shift.feature
│   ├── release_decision.feature
│   └── rollback_decision.feature
├── steps/
│   ├── data_steps.py
│   ├── model_steps.py
│   ├── serving_steps.py
│   └── observability_steps.py
└── conftest.py
```

### 7-11. 핵심 BDD Scenario

```gherkin
Feature: 후보 모델 배포 판단

  Scenario: Precision은 개선되지만 Recall 기준을 만족하지 못한다
    Given 동일한 data revision과 test dataset으로 평가된 baseline과 candidate가 있다
    When 두 model의 release metric을 비교한다
    Then candidate Precision은 baseline보다 높다
    And candidate Recall은 release 기준을 만족하지 못한다
    And release decision은 자동 승인되지 않는다
```

마지막 `Then`은 `aiqa-qa`의 release evaluation use case 결과를 검증하며 step definition 자체에서 승인 규칙을 계산하지 않는다.

추가 scenario는 다음 behavior를 고정한다.

- GE strict validation 실패 시 training dataset을 publish하지 않음
- 의도적으로 degraded된 dataset은 evidence로 보존함
- VM 시작 상태에서 baseline model이 같은 API URL로 응답함
- Candidate 배포 후 model version과 telemetry label이 함께 바뀜
- Current-shift traffic 후 high-risk rate가 baseline 범위를 벗어남
- Invalid traffic이 API error rate와 validation event를 증가시킴
- Rollback 후 baseline model version과 health가 복구됨

### 7-12. Test 실행 계층

```bash
uv run pytest -m "not integration and not e2e"
uv run pytest -m integration
uv run pytest tests/bdd
uv run pytest -m e2e
```

Docker, k3s 또는 외부 URL이 필요한 test는 marker로 분리한다. Test coverage는 품질 guardrail로 사용하되 숫자 자체를 목표로 삼지 않고 domain invariant와 application branch의 누락을 우선 검토한다.

Root dev dependency에는 pytest, pytest-bdd와 coverage 측정 도구를 두고 app/package가 별도 test runner를 만들지 않는다. BDD tag는 pytest marker에 매핑하여 `integration`, `e2e`, `requires_docker`, `requires_k3s` 실행 범위를 통제한다.

## 8. 데이터 설계

### 8-1. 원본 데이터

원본 `human_vital_signs_dataset_2024.csv`는 200,020행이며 timestamp와 Patient ID가 모두 고유하다. Timestamp는 2024-03-03부터 2024-07-19 범위이고 원본 파일은 최신 시각부터 역순으로 정렬되어 있다.

```text
data/raw/human_vital_signs_dataset_2024.csv
```

원본은 약 37MB이고 변경 가능성이 낮으므로 Git에서 관리한다.

### 8-2. 상위 Snapshot

Timestamp를 오름차순으로 정렬한 뒤 시간 기준 90:10으로 분리한다.

| Snapshot | 행 수 | 역할 |
| --- | ---: | --- |
| Model development | 180,018 | EDA, baseline/candidate 학습과 평가 |
| Operational | 20,002 | API traffic, monitoring과 release 판단 |

기준 시각은 `2024-07-06 00:32:45.779851` 부근이며 source timestamp에 timezone이 없으므로 실제 UTC로 해석하지 않고 순서와 cutoff에만 사용한다.

### 8-3. Model Development Split

Model development snapshot 내부는 label 비율을 유지하고 `random_state=42`로 분할한다.

| Dataset | 원본 전체 비율 | 행 수 | 역할 |
| --- | ---: | ---: | --- |
| `evaluation_baseline` | 10% | 20,002 | 1장 EDA와 평가 가능 여부 |
| `train` | 55% | 110,011 | baseline/candidate 학습 |
| `valid_baseline` | 15% | 30,003 | 설정과 threshold 선택 |
| `test` | 10% | 20,002 | 공통 최종 평가 |

`valid_degraded`는 `valid_baseline`에서 null, range와 label 오류를 주입한 복사본이다. 별도 원본 split으로 취급하지 않는다.

### 8-4. Operational Split

Operational snapshot은 model 개발에서 완전히 격리한다.

| Pool | 비율 | 행 수 | 역할 |
| --- | ---: | ---: | --- |
| Baseline pool | 40% | 8,001 | 평상시 traffic |
| Current pool | 40% | 8,001 | 입력 구성 변화와 invalid 요청 |
| Release holdout | 20% | 4,000 | 회귀 테스트와 최종 재평가 |

Operational 데이터는 학습, model 선택과 threshold tuning에 사용하지 않는다.

### 8-5. Data Lineage

```text
raw
├── model_development_snapshot
│   ├── evaluation_baseline
│   ├── train ────────────────→ baseline/candidate
│   ├── valid_baseline ───────→ valid_degraded
│   └── test ─────────────────→ 공통 최종 metric
└── operational_snapshot
    ├── baseline_pool ────────→ baseline traffic
    ├── current_pool ─────────→ current/invalid traffic
    └── release_holdout ──────→ regression과 재평가
```

## 9. DVC, Great Expectations와 MLflow

### 9-1. DVC 범위

DVC는 데이터 version과 data pipeline만 담당한다. Remote 없이 local cache를 사용하며 원본은 Git에서 가져온다.

```text
dvc.yaml
├── snapshot
├── split
├── degrade
├── operational
└── validate
```

`params.yaml`은 cutoff, split ratio와 seed를 관리한다. `dvc.lock`은 stage command와 input/output hash를 기록한다.

공식 실행은 Python wrapper로 제공한다.

```bash
uv run python scripts/prepare_data.py
```

개발자와 DVC Demo에서는 다음 명령을 사용한다.

```bash
uv run dvc repro
uv run dvc dag
uv run dvc status
```

### 9-2. Great Expectations 범위

Great Expectations는 데이터 정제기가 아니라 검증 evidence 생성기다.

- baseline expectation suite
- degraded expectation suite 또는 checkpoint
- 필수 column, null, type, range, label, row count와 identifier 검사
- Validation Result와 Data Docs 생성
- strict publish 실패 시 non-zero exit code

교육용 degraded dataset과 invalid request는 의도된 실패 evidence이므로 자동 삭제하지 않는다.

### 9-3. MLflow 범위

MLflow는 model experiment와 artifact의 기준 저장소다.

- local SQLite backend
- local filesystem artifact store
- baseline/candidate run
- dataset name, source, digest와 context
- model parameters, threshold와 metric
- model artifact와 metadata

각 run에는 다음 provenance를 기록한다.

```text
git_commit
dvc_lock_revision
raw_data_hash
train_data_hash
validation_data_hash
test_data_hash
split_seed
model_profile
threshold
```

### 9-4. 도구 책임 구분

```text
DVC                 어떤 데이터와 pipeline revision인가
Great Expectations  데이터가 어떤 규칙을 통과하거나 실패했는가
MLflow              그 데이터로 어떤 model과 metric을 만들었는가
```

## 10. Baseline과 Candidate Model

### 10-1. 내부 Bootstrap

Baseline과 candidate 생성 과정은 repository 내부 구현이며 강의 내용에서 profile 탐색 과정을 설명하지 않는다.

```bash
uv run python scripts/bootstrap_models.py
```

```text
artifacts/models/
├── baseline/
│   ├── model.joblib
│   └── metadata.json
├── candidate/
│   ├── model.joblib
│   └── metadata.json
└── deployed/
    ├── model.joblib
    └── metadata.json
```

### 10-2. Model 계약

- Baseline과 candidate는 서로 다른 실제 model bundle이다.
- 두 모델은 같은 train/validation/test 계약을 사용한다.
- Candidate는 Precision이 개선되지만 Recall 또는 guardrail이 악화될 수 있다.
- Metric과 prediction rate는 실제 prediction으로 계산한다.
- 목표 숫자를 JSON에 하드코딩하지 않는다.
- Scenario test는 정확한 한 값보다 방향과 허용 범위를 검증한다.
- 초기 `deployed` model은 baseline이다.

### 10-3. Metric 책임

- Precision, Recall, F1과 confusion matrix는 model evaluation에서 계산한다.
- `high_risk` rate는 model output과 traffic 구성에서 계산한다.
- API error rate는 invalid traffic과 HTTP response에서 계산한다.
- Latency는 실행 환경 영향을 받으므로 baseline 대비 변화와 limit으로 판단한다.

## 11. 수강생 실습 환경과 URL

### 11-1. 수강생이 보는 환경

수강생은 개인 PC의 VS Code와 browser만 사용한다. VS Code Remote-SSH로 Bastion을 거쳐 제공된 개인 VM에 접속한다.

```text
개인 PC
├── VS Code Remote-SSH ── Bastion ── 개인 VM terminal
└── Browser ──────────────────────── 제공된 service URL
```

VM에는 다음이 준비되어 있다.

- `tta-aiqa` repository
- uv와 Python
- DVC local cache
- Docker
- k3s와 kubectl
- MLflow
- baseline model과 risk-api

VM이 어떤 virtualization platform에서 생성되었는지는 수강생에게 설명하지 않는다.

### 11-2. 학생별 URL 수

과거 `legacy/domains.csv`에는 30개 VM과 학생별 app/MLflow hostname이 각각 두 계열씩 정의되어 있다. V2에서는 학생에게 하나의 canonical 계열만 안내한다.

학생별 전용 hostname은 2개다.

| 서비스 | 개수 | 역할 |
| --- | ---: | --- |
| Risk API/KServe | 1 | `/docs`, `/health`, `/predict`, `/metrics` |
| MLflow | 1 | run, metric, dataset과 model artifact |

공용 hostname은 2개다.

| 서비스 | 개수 | 구분 방식 |
| --- | ---: | --- |
| Argo CD | 1 | 학생별 Application과 RBAC |
| Grafana | 1 | `student_id` dashboard variable |

교재 사이트 URL은 별도 공용 링크다. 한 학생이 받는 정보는 다음으로 제한한다.

```text
VS Code SSH alias 1개
개인 API URL 1개
개인 MLflow URL 1개
공용 Argo CD URL 1개
공용 Grafana URL 1개
교재 URL 1개
```

### 11-3. URL 정책

- Baseline과 candidate는 같은 API URL을 사용한다.
- Model 배포와 rollback 후 `model_version`이 바뀌는지 확인한다.
- API docs, health와 metrics는 별도 domain이 아니라 path로 제공한다.
- `homelab` 계열 hostname과 SSH stream port는 학생 문서에서 숨긴다.
- 실제 hostname은 repository에 하드코딩하지 않고 환경별 value로 주입한다.
- Course 문서는 “강사가 제공한 URL”로 표현한다.

### 11-4. Telemetry 구분

모든 log, metric과 trace에 다음 label을 공통으로 둔다.

```text
student_id
service
environment
model_role
model_version
model_run_id
```

Grafana dashboard는 `student_id`를 기본 variable로 사용한다.

## 12. 배포 구조

### 12-1. Compose

Compose는 강사 검증, app별 local smoke test와 Docker 개념 실습에 사용한다.

```text
core profile
  MLflow, trainer, API, traffic

observability profile
  Alloy와 local 또는 제공된 telemetry endpoint 연결
```

### 12-2. Kubernetes와 Argo CD

수강생 VM의 k3s에는 baseline model이 이미 배포되어 있다. 수강생은 manifest와 live state를 확인하고 candidate 변경을 GitOps로 반영한다.

```text
Git desired state
  -> Argo CD diff
  -> sync
  -> k3s resource health
  -> endpoint smoke
  -> telemetry 확인
```

Argo CD가 관리하는 resource를 수강생이 `kubectl apply`로 임의 변경하여 바로 되돌아가는 상황을 피하도록 Lab namespace 또는 manual sync 정책을 사용한다.

### 12-3. KServe 범위

- 기존 Kubernetes 모델 배포 과정 안에서 다룬다.
- 환경이 준비되면 live `InferenceService`와 endpoint를 확인한다.
- 실행이 불가능한 경우 manifest inspection과 prepared evidence로 범위를 제한한다.
- Argo CD와 KServe를 별도 신규 교시로 만들지 않는다.

## 13. 교육 진행

### 13-1. 1일차

| 교시 | 기존 커리큘럼 | V2 실습 연결 |
| --- | --- | --- |
| 1교시 | AI 품질의 개요 | baseline/candidate 운영 사건 소개 |
| 2교시 | 데이터 품질의 중요성 | development/operational 데이터 역할 구분 |
| 3교시 | 데이터 품질 확인 실습 | Notebook과 Pandas EDA |
| 4교시 | 데이터 검증 자동화 | GE baseline/degraded 검증 |
| 5교시 | 모델 품질 지표 이해 | Precision, Recall, F1, FP/FN, threshold |
| 6교시 | 모델 성능 평가 실습 | 실제 baseline/candidate 공통 test 비교 |
| 7교시 | 모델 실험 관리 | DVC revision과 MLflow run 연결 |

DVC는 7교시의 “데이터셋 변경에 따른 성능 변화 추적”을 구체화하며 별도 교시를 추가하지 않는다.

### 13-2. 2일차

| 교시 | 기존 커리큘럼 | V2 실습 연결 |
| --- | --- | --- |
| 1교시 | 컨테이너와 모델 서빙 | trainer/API container와 artifact 분리 |
| 2교시 | API 구성 | FastAPI contract, model version과 correlation ID |
| 3교시 | Kubernetes 기본 | Pod, Deployment, ConfigMap과 manifest |
| 4교시 | 모델 배포 실습 | baseline 상태와 candidate GitOps sync |
| 5교시 | 운영 품질의 위협 요인 | current-shift와 invalid traffic |
| 6교시 | 로그와 지표의 수집 | JSONL, Prometheus, Loki와 trace 연결 |
| 7교시 | Dashboard와 이상 대응 | Grafana 비교와 유지/보류/되돌림 판단 |

### 13-3. 수강생에게 노출하는 것

- VS Code Remote-SSH 접속
- Notebook EDA
- DVC revision과 DAG
- GE expectation과 Validation Result
- baseline/candidate metric과 MLflow UI
- Dockerfile, API와 Kubernetes manifest
- Argo CD diff, sync와 resource health
- traffic 실행과 Grafana dashboard
- 품질 이상 원인 후보와 대응 판단

### 13-4. 내부 코드로만 제공하는 것

- snapshot과 split 구현 세부사항
- baseline/candidate profile 탐색
- 목표 metric 관계를 만족하는 설정 선정
- prepared evidence 생성
- traffic 분포 조정 알고리즘
- VM provisioning과 실제 domain inventory

## 14. 실행 Workflow

### 14-1. 강사 및 개발자 준비

```bash
uv sync
uv run python scripts/setup_course.py
```

`setup_course.py`는 다음을 조립하는 내부 wrapper다.

```text
dvc repro로 snapshot, split, scenario와 GE evidence 생성
  -> baseline/candidate bootstrap
  -> MLflow 기록
  -> baseline deploy 상태 확인
  -> baseline traffic과 telemetry seed
```

### 14-2. 수강생 시작 상태

- Repository와 dependency 준비 완료
- DVC output과 GE evidence 준비 완료
- Baseline/candidate MLflow run 준비 완료
- Baseline model 배포와 API health 정상
- Baseline traffic과 telemetry 기준선 존재
- Grafana 연결 후 학생별 dashboard에서 기준선 확인 가능

수강생은 bootstrap을 학습하지 않고 준비된 상태를 확인하며 시작한다.

### 14-3. 수강생 기본 확인

```bash
pwd
git status
uv --version
uv run dvc status
kubectl get pods -A
echo "$API_URL"
curl -s "$API_URL/health"
```

Browser UI는 localhost tunnel이 아니라 강사가 제공한 URL을 사용한다.

## 15. 생성물과 Git 정책

### 15-1. Git에서 관리할 것

- source code와 tests
- raw source CSV
- DVC metadata와 params
- GE expectation과 checkpoint
- Notebook source
- generic Compose, Kubernetes와 GitOps manifest
- dashboard definition과 query
- README와 기획 문서

### 15-2. Git에서 제외할 것

- DVC cache와 generated snapshot/split
- GE runtime result와 generated Data Docs
- model binary와 metadata output
- MLflow DB와 run artifact
- JSONL event, metric과 trace output
- student assignment, IP, 실제 domain과 credential
- Notebook execution cache와 generated HTML

### 15-3. Prepared Evidence

수업에 필요한 고정 evidence를 Git에 포함해야 한다면 일반 runtime output과 분리한다.

```text
reference/
└── evidence/
    ├── data-quality/
    ├── model-evaluation/
    ├── deployment/
    └── observability/
```

Prepared evidence에는 생성 command, source revision과 확인 범위를 함께 기록한다.

## 16. AS-IS에서 TO-BE로 이동

### 16-1. 주요 이동

| AS-IS | TO-BE |
| --- | --- |
| `apps/simple_mlops/app.py` | `apps/risk-api` 내부 모듈 |
| `apps/simple_mlops/train.py` | `apps/model-trainer` |
| `apps/simple_mlops/send_fake_traffic.py` | `apps/traffic-generator` |
| `apps/simple_mlops/compose.yaml` | `deploy/compose/simple-mlops` |
| `apps/simple_mlops/alloy...` | `deploy/compose/simple-mlops` |
| data preparation wrapper | `apps/data-quality-pipeline` + `aiqa-data` |
| feature/label 상수 | `aiqa-core` |
| training과 MLflow 로직 | `aiqa-model` |
| prediction use case | `aiqa-serving` |
| event, metric과 trace | `aiqa-observability` |
| release report와 approval rule | `aiqa-qa` |
| legacy의 외부 기술 구현 | 각 bounded context의 `adapters/` |
| root 파생 CSV | DVC managed output 경로 |
| app 내부 model/event 폴더 | root `artifacts/` |

### 16-2. 현재 Package 보완

- `aiqa-data`에서 reference model 학습과 operational event 생성을 제거한다.
- `aiqa-model`을 model profile, evaluation, loading과 MLflow adapter로 세분화한다.
- `aiqa-observability/runtime.py`를 event, metrics와 tracing module로 분리한다.
- `aiqa-serving`을 새로 만들고 HTTP와 독립된 prediction use case를 이동한다.
- `aiqa-qa`를 만들고 release evidence와 decision rule을 legacy 구현과 분리해 다시 정의한다.
- Legacy에서 선별해 가져오는 filesystem, MLflow, GE, FastAPI와 observability 연동 구현은 해당 package의 `adapters/` 아래에 재배치한다.
- Repository path에 의존하는 core helper를 app settings 또는 명시적 argument로 교체한다.
- Root workspace에는 네 app과 여섯 package만 member로 등록한다.
- Workspace lock은 root `uv.lock` 하나를 기준으로 한다.

## 17. 구현 단계

### 17-1. Phase 1: 기준과 Workspace

- V2 branch 생성
- root workspace와 dependency group 정리
- target directory scaffold 생성
- bounded context와 public API 계약 정의
- `docs/adr/`와 첫 Architecture Decision Record 작성
- import direction과 layer architecture test를 먼저 추가
- pytest marker와 `pytest-bdd` test scaffold 추가
- 핵심 BDD feature를 pending scenario로 작성
- generated path와 `.gitignore` 정책 적용

### 17-2. Phase 2: Data와 DVC

- raw CSV 이동과 path 정리
- DVC 초기화, `params.yaml`, `dvc.yaml` 작성
- temporal snapshot과 deterministic split unit test 작성
- data leakage, row count와 hash contract test 작성
- 실패 test를 기준으로 snapshot/split use case 구현
- degraded/operational scenario test와 구현
- data quality gate BDD scenario 연결

### 17-3. Phase 3: GE와 1일차 Lab

- Data Quality Pipeline app 생성
- expectation suite와 checkpoint 작성
- GE adapter contract test 작성
- baseline/degraded Validation Result와 Data Docs integration test
- strict publish와 evidence 보존 BDD scenario 통과
- EDA Notebook 작성
- 1일차 Lab과 README 연결

### 17-4. Phase 4: Model과 MLflow

- Model Trainer app 생성
- model domain invariant와 evaluation use case test를 먼저 작성
- baseline/candidate profile 확정
- common test evaluation과 scenario range test 통과
- MLflow dataset, run, model과 DVC provenance 연결
- MLflow adapter contract와 integration test 추가
- candidate evaluation BDD scenario 통과
- initial deployed baseline publish

### 17-5. Phase 5: Serving과 Traffic

- `aiqa-serving` package 생성
- prediction use case와 port test를 먼저 작성
- Risk API module 분리와 FastAPI adapter integration test
- model reload와 response/event contract 검증
- Traffic Generator scenario behavior test와 네 scenario 구현
- baseline serving과 operational shift BDD scenario 통과
- API contract와 integration test 추가

### 17-6. Phase 6: Deployment와 Observability

- Compose stack 이동
- Kubernetes/Kustomize와 Argo CD asset 정리
- student/model/trace label 계약 적용
- Grafana dashboard와 query 정리
- observability adapter contract test 추가
- baseline/candidate deploy와 rollback BDD 및 smoke test

### 17-7. Phase 7: 교재와 End-to-End

- `aiqa-qa` domain/application test와 release decision use case 구현
- Release Decision Lab adapter와 BDD scenario 연결
- `ttamlops-2607`의 명령과 경로를 V2에 맞게 갱신
- VS Code Remote-SSH와 제공 URL 기준으로 접속 문서 수정
- localhost tunnel과 실제 domain hardcoding 제거
- 2일 14교시 흐름 검증
- 전체 BDD feature와 end-to-end test 실행
- 준비 상태 reset과 전체 smoke test 실행

## 18. 완료 기준

### 18-1. 기능 완료 기준

- DVC가 raw에서 모든 dataset과 GE evidence를 재현한다.
- Development와 operational 데이터 leakage가 없다.
- Baseline/candidate가 실제 model bundle과 MLflow run으로 생성된다.
- Candidate의 선택적 metric 개선과 guardrail 악화가 재현된다.
- Baseline model이 초기 상태에서 배포되어 있다.
- 같은 URL에서 candidate 배포와 baseline rollback을 확인할 수 있다.
- Traffic scenario가 의도한 validation, distribution과 error 신호를 만든다.
- Log, metric과 trace를 student/model/request 기준으로 연결할 수 있다.
- 최종 판단에 risk, owner, next action과 재평가 조건이 포함된다.

### 18-2. 구조 완료 기준

- `apps/simple_mlops`의 세 process가 독립 app으로 분리된다.
- `simple-mlops` 이름은 Compose stack에만 남는다.
- Package와 app import 방향이 단방향이다.
- App별 dependency와 Docker image가 분리된다.
- Root workspace lock 하나로 전체 환경을 재현한다.
- Generated data와 runtime artifact가 Git status에 나타나지 않는다.
- `legacy` import 없이 모든 app, test와 Lab이 동작한다.
- Domain과 application layer가 framework/vendor SDK를 import하지 않는다.
- Filesystem, database, network와 vendor SDK 구현은 각 package의 `adapters/` 아래에만 존재한다.
- 모든 app이 composition root에서 port와 adapter를 명시적으로 조립한다.

### 18-3. 검증 완료 기준

```text
uv lock / uv sync
Ruff
package unit tests
app unit tests
architecture dependency tests
port/adapter contract tests
DVC repro and status
GE success/failure integration tests
baseline/candidate reproducibility tests
trainer/API integration tests
traffic scenario range tests
BDD acceptance scenarios
Compose smoke test
Kubernetes manifest render and validation
Argo CD/KServe live 또는 inspection test
Grafana query와 dashboard validation
README command replay
```

### 18-4. Engineering 완료 기준

- 새 use case는 실패하는 unit 또는 acceptance test에서 시작한다.
- Domain invariant는 framework 없이 unit test로 설명할 수 있다.
- Adapter는 자신이 구현하는 port의 contract test를 통과한다.
- Bounded context 간 dependency는 허용된 방향만 사용한다.
- BDD scenario는 수강생 또는 QA 담당자가 이해할 수 있는 business language로 작성한다.
- Gherkin step에 business rule을 구현하지 않고 application use case를 호출한다.
- Bug fix에는 같은 문제를 재현하는 regression test가 포함된다.
- Test fixture는 deterministic하며 clock, UUID와 random을 통제한다.
- Refactor 후 architecture, unit, contract와 관련 BDD test를 모두 재실행한다.
- Coverage 수치는 보조 지표이며 behavior와 branch 누락 검토를 대체하지 않는다.

## 19. Version Control과 보류 사항

### 19-1. Branch와 Commit 원칙

V2 구현은 `main`에 직접 커밋하지 않는다. TO-BE 계획 승인 후 `main` 기준의 별도 feature branch를 만들고 다음 순서로 커밋한다.

```text
1. V2 planning document
2. architecture tests, BDD features and workspace foundation
3. data/DVC behavior and tests
4. apps, packages and contract tests
5. deployment, observability and acceptance tests
6. labs, docs and end-to-end verification
```

Implementation과 해당 test는 같은 변경 단위로 commit한다. 구조 변경만 하고 test를 나중 commit으로 미루지 않는다. 현재 문서 정리 단계에서는 branch 생성과 commit을 수행하지 않는다.

### 19-2. 구현 전 확정할 항목

- Baseline/candidate metric의 허용 범위
- Candidate 선택 algorithm과 threshold profile
- Grafana 공용 URL과 학생별 dashboard 권한 방식
- Argo CD Application 이름과 학생 RBAC 규칙
- `apps.learn` 계열 canonical domain 확정
- KServe live 실습 범위와 fallback 조건
- Prepared evidence를 Git에 포함할 최소 범위
- Course 시작 상태 reset과 검증 command
- Architecture test를 AST로 유지할지 전용 import boundary 도구를 도입할지
- Domain/application test coverage의 최소 guardrail
