# TTA AIQA V2 TO-BE Plan

이 문서는 `tta-aiqa` V2의 교육 시나리오, monorepo 구조, 데이터와 모델 계보, 실행 환경, 수강생 동선과 구현 순서를 정의하는 단일 기획 문서다. 기존 package 분리 계획과 monorepo 초안을 이 문서로 통합한다.

## 1. 목표

### 1-1. V2 목표

기존 2일 교육과정의 주제와 순서는 유지한다. Repository 내부 구현을 실제 데이터, 실제 baseline과 두 candidate model, 실제 API, GitOps 배포와 운영 관측 신호가 하나의 품질 판단 사건으로 이어지도록 재구성한다.

```text
기준 데이터 품질 확인
  -> 데이터 검증 자동화
  -> baseline과 두 candidate 모델 평가
  -> 데이터 revision과 MLflow run 연결
  -> Candidate A 보류와 Candidate B 승인
  -> 승인된 Candidate B 배포 확인
  -> Alloy 연결과 개인 Grafana Cloud dashboard import
  -> 운영 traffic과 telemetry 누적 확인
  -> 품질 이상 원인 후보와 대응 판단
```

### 1-2. 변경 원칙

- 공개 커리큘럼은 기존 2일 14교시 구성을 유지한다.
- DVC만 기존 모델 실험 관리 구간에 추가한다.
- 수강생은 모델 개발자가 아니라 AI 서비스 품질/운영 담당자 역할을 맡는다.
- `apps/`는 독립 실행 process, `packages/`는 재사용 로직을 소유한다.
- 교육용 수치는 하드코딩하지 않고 고정된 데이터, versioned configuration과 코드에서 계산한다.
- 교육 문서의 model metric, threshold, confusion matrix와 운영 기준값은 PhysioNet 원본에서 실제 생성한 benchmark evidence를 기준으로 갱신한다.
- Clean Architecture와 DDD dependency 규칙을 자동 test로 강제한다.
- Use case와 교육 scenario는 pytest 기반 TDD로 구현한다.
- 유료 managed service를 필수 경로로 사용하지 않고 monitoring은 Grafana Cloud의 비용 없는 교육 범위에서 진행한다.
- `tmp/legacy/`는 archive이며 새 코드에서 import하지 않는다.

### 1-3. 범위 밖

- VM 생성, clone, DNS와 network는 `mrml-infra` 책임이다.
- Proxmox 구조와 사용법은 수강생 교육 내용에 포함하지 않는다.
- 실제 학생 계정, IP, domain inventory와 credential은 두 교육 repository에 저장하지 않는다.
- JupyterLite는 V2 필수 범위에 포함하지 않는다.
- DVC remote와 유료 object storage는 사용하지 않는다.
- Grafana, Loki, Tempo와 Prometheus server를 repository 또는 수강생 VM에 배포하지 않는다.
- Repository가 관리하는 telemetry collector는 Alloy까지이며 Grafana Cloud backend 운영은 교육 범위에 포함하지 않는다. 다만 dashboard template과 import 도구는 실습 자료로 관리한다.

### 1-4. 이번 검토 결정

| 항목 | 상태 | 결정 |
| --- | --- | --- |
| 기준 데이터 | 확정 | Kaggle Human Vital Sign Dataset을 PhysioNet Challenge 2012 Set A로 교체 |
| Model scenario | V2 확정 | V1 `HOLD/HOLD` evidence는 보존하고 V2 sealed test에서 Candidate A `HOLD`, Candidate B `APPROVE`를 확정 |
| Baseline feasibility | Phase 0 통과 | Dummy 대비 repeated-CV PR-AUC 신호를 확인했으며 evidence에 불확실성 기록 |
| GE blocking gate | 제외 | 실제 raw/processed 품질 evidence로 사용하고 V2 교육 경로에서 dataset publish를 차단하지 않음 |
| Degraded dataset | 제외 | 임의 null/range/label 오류를 주입한 `valid_degraded`를 생성하지 않음 |
| 교육 수치 | V2 확정 | V2 canonical benchmark의 threshold, metric과 confusion matrix를 교재 기준으로 사용 |
| Feature preparation | 내부 구현 | Phase 0의 133개 available feature를 v1으로 재현하고 model input 확정 과정은 코드와 evidence로만 보존하며 교육과정에는 추가하지 않음 |
| Test 방법 | 확정 | 별도 scenario framework 없이 pytest 기반 TDD만 사용 |
| Validation dataset 이름 | 확정 | `valid`로 통일 |
| Configuration | 확정 | Feature, model profile, traffic, release policy와 telemetry 설정을 versioned file로 관리 |
| Runtime settings | 확정 | Python app은 `pydantic-settings`로 environment, endpoint와 config path를 typed validation |
| Secret injection | 확정 | Kubernetes Secret을 app별 read-only volume으로 mount하고 `secrets_dir`로 로드 |
| 강사 제공 실습 URL | 확정 | 학생별 Risk API 1개와 MLflow 1개, 총 2개 |
| Monitoring | 확정 | 각 수강생이 개인 Grafana Cloud account를 만들고 Alloy를 자신의 stack에 연결 |
| Dashboard 실습 | 확정 | 수강생이 자신의 Grafana Cloud에 dashboard를 import하고 telemetry 누적을 확인 |
| Monitoring backend 배포 | 제외 | Grafana, Loki, Tempo와 Prometheus server를 직접 배포하지 않음 |
| Serving topology | 확정 | 외부 Risk API가 내부 KServe를 호출하고 Compose는 local model adapter 사용 |

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

- `tmp/legacy/` 파일을 새 app과 package가 import하지 않는다.
- 기존 labs, demos, package, artifact를 일괄 복원하지 않는다.
- 필요한 규칙, test case, manifest, Alloy 구성과 Grafana Cloud dashboard import를 새 구조로 다시 구현한다.
- `tmp/legacy/domains.csv`는 과거 환경 inventory 참고 자료로만 사용한다.
- 중복 Notebook, JupyterLite mirror, 생성 HTML과 과거 runtime artifact는 기본 이관 대상이 아니다.

## 3. 교육 시나리오

### 3-1. 공통 사건

ICU 입원 환자의 병원 내 사망 위험을 예측하는 API는 baseline 모델로 운영 중이다. MLflow에는 서로 다른 두 candidate가 기록되어 있다. Candidate A는 Precision 중심 profile이고 Candidate B는 균형 profile이다. 수강생은 같은 환자 단위 데이터 계약과 release 기준으로 두 candidate를 평가한다.

수강생은 다음 질문에 답한다.

```text
어떤 candidate를 보류해야 하는가?
어떤 candidate를 승인하고 배포할 수 있는가?
배포 후 model version과 운영 신호가 승인된 candidate를 가리키는가?
어떤 조건에서 baseline으로 되돌려야 하는가?
```

목표 교육 결과는 다음과 같다. 아직 확정된 사실이 아니며 이름 자체에 판단 결과를 넣지 않고 실제 metric과 release policy가 결과를 결정한다.

| Model | Profile | 목표 판단 | 후속 동작 |
| --- | --- | --- | --- |
| Baseline | 현재 운영 기준 | 초기 배포 상태 | Candidate 비교 기준 |
| Candidate A | Precision 중심 | Recall 또는 guardrail 미충족으로 보류 | 원인과 재평가 조건 기록 |
| Candidate B | 균형 profile | 필수 release 기준 충족으로 승인 | 같은 API URL에 GitOps 배포 |

Canonical benchmark가 이 관계를 실제로 재현한 경우에만 Candidate B 배포 후 current-shift와 invalid traffic을 보내 운영 신호를 확인한다. 이 변화는 입력 구성과 API validation 문제를 재현하며 Candidate B 자체 결함으로 단정하지 않는다. Model-specific guardrail이 유지되는 공통 시나리오의 목표 결론은 Candidate B 배포 유지와 입력 품질 후속 조치다. Rollback trigger와 baseline 복구 경로는 별도 smoke test로 검증한다.

V1 canonical 결과는 Candidate A와 Candidate B 모두 `HOLD`였으며 변경하지 않고 historical evidence로 보존한다. 승인된 V2 split revision은 V1의 sealed test를 재사용하지 않고 400건의 새 sealed test 역할을 동결했다. V2 test에서 Candidate A는 recall guardrail과 false-negative reduction을 충족하지 못해 `HOLD`, Candidate B는 PR-AUC `0.5743`, precision `0.3793`, recall `0.8000`, false negative `11`로 모든 필수 기준을 충족해 `APPROVE`다. `docs/reference/evidence/model/revisions/v2/canonical-benchmark.json`의 `deployment_allowed`는 `true`, `post_test_tuning_allowed`는 `false`다.

### 3-2. 시나리오 성립 조건

PhysioNet 2012 Set A는 ICU stay 4,000건, 사망 554건의 작은 불균형 데이터다. Raw measurement는 풍부하지만 patient-level model sample은 4,000건이므로 model 성능과 Candidate 관계를 미리 보장하지 않는다.

```text
F0 Data feasibility
  patient/outcome join, target support와 leakage 검증

F1 Predictive feasibility
  Dummy baseline 대비 non-trivial model의 cross-validation 신호 검증

F2 Scenario feasibility
  train/valid에서 Candidate A/B의 목표 metric 관계 검증

F3 Final confirmation
  profile/policy freeze 후 test 1회 평가로 canonical evidence 확정
```

F1 또는 F2가 실패하면 전체 monorepo 구현을 계속하기 전에 aggregation, missing policy, feature contract와 model family를 train/valid 범위에서 재검토한다. Test 결과를 본 뒤 threshold나 release policy를 완화하지 않는다. 제한된 탐색 후에도 관계가 성립하지 않으면 Candidate B를 억지로 승인하지 않고 `HOLD/HOLD` 또는 baseline 유지 시나리오로 교재를 수정한다.

이 모델은 교육용 품질 판단 시스템이며 임상적 유효성이나 실제 의료 사용 가능성을 주장하지 않는다. Baseline이 Dummy보다 낫다는 사실도 임상적 유용성을 의미하지 않는다.

### 3-3. 판단 근거

- PhysioNet raw record의 measurement coverage, missing sentinel, range, timestamp와 outcome join 상태
- Great Expectations raw ingestion/processed readiness validation 결과
- baseline, Candidate A와 Candidate B의 Precision, Recall, F1, FP/FN과 threshold
- DVC data revision과 MLflow dataset/run lineage
- container, API contract와 model metadata
- Kubernetes desired/live state와 Argo CD sync 결과
- endpoint response, model version, request ID와 trace ID
- error rate, latency, score와 prediction distribution
- Grafana Cloud 화면과 상세 log/metric/trace

### 3-4. 결론 표현

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
│   ├── kserve-predictor/
│   ├── traffic-generator/
│   └── grafana-dashboard-importer/
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
│   ├── interim/
│   ├── processed/
│   ├── splits/
│   └── traffic/
├── artifacts/
│   ├── data-quality/
│   ├── features/
│   ├── models/
│   ├── mlflow/
│   ├── events/
│   ├── metrics/
│   ├── traces/
│   └── reports/
├── configs/
│   ├── README.md
│   ├── contracts/physionet-record.yaml
│   ├── contracts/model-input.yaml
│   ├── data/aggregation.yaml
│   ├── data/quality-rules.yaml
│   ├── model/feature-sets.yaml
│   ├── model/profiles.yaml
│   ├── model/evaluation.yaml
│   ├── serving/api.yaml
│   ├── traffic/scenarios.yaml
│   ├── qa/release-policy.yaml
│   └── observability/telemetry.yaml
├── deploy/
│   ├── compose/simple-mlops/
│   ├── kubernetes/
│   ├── gitops/
│   └── grafana-cloud/
│       ├── dashboards/ai-quality.json
│       └── README.md
├── scripts/
├── tests/
│   ├── architecture/
│   ├── characterization/
│   ├── scenarios/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── adr/
│   ├── feature-contract-working-note.md
│   └── v2-to-be-plan.md
├── tmp/
│   └── legacy/
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

### 4-3. Configuration as Code

교육 조건과 변경 가능한 정책은 Python 상수로 흩어놓지 않고 versioned configuration file로 관리한다.

| 형식 | 용도 |
| --- | --- |
| YAML | model input 계약, data rule, model profile, traffic scenario와 release policy |
| JSON | Grafana Cloud dashboard처럼 외부 도구가 직접 소비하는 native document |
| TOML | `pyproject.toml`과 Python tool 설정 |
| Environment/.env | URL, token, credential과 VM별 runtime 값 |

`settings.py`는 config path와 environment 값을 typed settings로 해석하는 역할만 맡는다. Feature 목록, threshold, model parameter, traffic 비율과 release 기준의 fallback 값을 Python에 중복 정의하지 않는다. `.env.example`에는 placeholder만 두고 실제 `.env`는 Git에서 제외한다.

| Configuration | 소유 Context/App |
| --- | --- |
| `contracts/physionet-record.yaml` | PhysioNet raw adapter contract |
| `contracts/model-input.yaml` | Shared Kernel contract |
| `data/aggregation.yaml` | Data Quality patient-level feature aggregation |
| `data/quality-rules.yaml` | Data Quality |
| `model/feature-sets.yaml` | Model Lifecycle 내부 feature subset 비교 |
| `model/profiles.yaml`, `model/evaluation.yaml` | Model Lifecycle |
| `serving/api.yaml` | Risk API와 Serving |
| `traffic/scenarios.yaml` | Traffic Generator |
| `qa/release-policy.yaml` | Release Assurance |
| `observability/telemetry.yaml` | Observability |
| `deploy/grafana-cloud/dashboards/*.json` | Grafana Dashboard Importer |

`configs/contracts/model-input.yaml`은 Data Quality, Model Lifecycle과 Serving이 공유하는 model input 계약의 단일 기준이다.

```yaml
schema_version: 1
target: in_hospital_death
labels:
  positive: death
  negative: survival
features:
  - name: age
    dtype: float
  - name: icu_type
    dtype: category
  - name: heart_rate__mean
    dtype: float
  - name: gcs__min
    dtype: float
  - name: urine__sum
    dtype: float
  - name: heart_rate__missing
    dtype: bool
```

Feature 계약은 available feature와 model input feature를 구분한다.

| 구분 | 의미 | 확정 시점 |
| --- | --- | --- |
| Available feature | Raw 시계열에서 생성 가능한 patient-level feature | Phase 0의 133개 구성을 v1으로 삼아 Phase 2에서 재현 |
| Model input feature | Available feature 중 실제 세 model과 serving이 사용하는 feature | Phase 4 내부 train/CV와 valid 검증 후 test 전에 동결 |

`aggregation.yaml`은 available feature 생성 규칙을 소유하고 `feature-sets.yaml`은 내부 비교용 subset을 소유한다. `model-input.yaml`은 최종 선택 결과를 순서, dtype과 null 정책까지 포함한 canonical serving 계약으로 기록한다. Phase 0에서는 세 model 모두 같은 133개 feature 전체를 사용했으며 production 구현도 이를 첫 기준으로 삼는다.

Feature diagnostics와 selection은 model을 준비하기 위한 내부 과정이다. Correlation, 결측률, 분산, coefficient, permutation importance와 subset 비교는 코드와 evidence로 남기지만 수강생 교육과정에는 포함하지 않는다. 탐색은 train/CV와 valid로 제한하고 aggregation, model input, model profile과 release policy를 동결한 뒤 sealed test를 한 번만 평가한다. Test 결과를 보고 feature를 추가·제거하지 않는다.

Raw measurement name, 단위, aggregation과 missing indicator의 관계는 data schema에서 관리하고 serving contract에는 동결된 patient-level model input만 노출한다. 구체적인 내부 판단 기록은 `docs/feature-contract-working-note.md`에 보존하고 canonical benchmark 이후 config와 evidence를 최종 기준으로 삼는다.

Configuration은 값을 제공하지만 domain invariant와 executable business rule을 대신하지 않는다. Adapter가 YAML/JSON을 읽고 schema를 검증한 뒤 `FeatureSet`, `ModelProfile`, `ReleasePolicy` 같은 typed domain value로 변환한다. Domain과 application layer는 file path, YAML parser와 environment variable을 직접 알지 않는다.

모든 관리 대상 configuration에는 `schema_version`을 두고 unknown key, 중복 feature, 잘못된 type과 범위를 fail-fast로 거부한다. App composition root는 config path를 CLI argument 또는 environment로 받고 package는 repository 상대 경로를 추측하지 않는다.

Model training, evaluation과 release evidence에는 사용한 config file의 SHA-256과 resolved snapshot을 기록한다. 따라서 feature, profile 또는 release threshold 변경이 data revision, MLflow run과 최종 판단에서 추적 가능해야 한다.

### 4-4. Runtime Settings와 Secret

설정은 성격에 따라 source와 검증 책임을 분리한다.

| 설정 종류 | 저장 및 주입 방식 | 검증 책임 |
| --- | --- | --- |
| Feature, data rule, model profile, release policy | Git에서 관리하는 YAML/TOML | Adapter가 읽고 Pydantic `BaseModel` schema로 검증 |
| Environment, endpoint, config path, 실행 mode | Environment variable | App별 Pydantic `BaseSettings` |
| Token, password와 credential | Local private `.env` 또는 Kubernetes Secret volume | App별 `BaseSettings`와 `SecretStr` |
| OCI registry pull credential | 강사가 사전 생성한 Kubernetes `imagePullSecret` | kubelet과 Pod/KServe Predictor spec만 사용 |
| Grafana dashboard definition | Git에서 관리하는 native JSON | Dashboard Importer adapter와 contract test |

Python app의 `settings.py`는 `pydantic-settings`를 사용한다. `BaseSettings`는 process를 실행하기 위한 runtime 값과 configuration file 경로만 소유한다. Feature 목록, threshold, model parameter와 품질 기준을 environment variable로 평탄화하거나 Python default로 중복 정의하지 않는다. 구조화된 YAML/TOML은 adapter가 별도 `BaseModel`로 검증하고 typed domain value로 변환한다.

```python
class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIQA_",
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/var/run/secrets/aiqa/risk-api",
    )

    environment: str = "local"
    model_profile_path: Path
    mlflow_tracking_uri: AnyHttpUrl
    api_token: SecretStr | None = None
```

각 app은 필요한 field만 가진 독립 settings class를 소유하고 `bootstrap.py`에서 한 번 생성한다. 생성된 settings와 adapter는 constructor/factory로 use case에 주입한다. Domain과 application layer는 `BaseSettings`, `os.environ`, `.env`, Secret file과 repository 상대 경로를 직접 읽지 않는다. `SecretStr`은 log와 representation의 우발적 노출을 줄이는 수단이며 secret 저장소나 암호화를 대신하지 않는다.

Pydantic의 기본 source 우선순위는 CLI parsing을 활성화한 경우 CLI가 가장 높고, 그다음 initializer, environment variable, `.env`, secrets directory, default 순서로 사용한다. 운영에서 `.env`가 mounted Secret을 덮어쓰지 않도록 다음 규칙을 강제한다.

- `.env`와 local secrets directory는 개발 및 개인 Grafana Cloud 설정에만 사용하고 Git과 container image에서 제외한다.
- 운영 container에는 `.env`를 복사하지 않고 Kubernetes Secret을 app별 `/var/run/secrets/aiqa/<app>`에 read-only로 mount한다.
- Secret key/file name은 settings field의 alias, prefix와 case-sensitivity 규칙에 맞추고 contract test로 검증한다.
- Pod에는 해당 process가 사용하는 key만 제공하고 다른 app의 credential directory를 공유하지 않는다.
- Secret volume은 non-root process가 읽을 수 있는 최소 권한으로 설정하고 mount path와 key contract만 manifest에서 관리한다.
- 실제 Secret 값과 값이 포함된 generated manifest는 GitOps repository에 commit하지 않는다. 교육 환경에서는 private `.env`를 입력으로 한 bootstrap command 또는 `kubectl create secret`로 사전 생성한다.
- Secret 변경 반영 방식은 명시적으로 결정한다. 시작 시 한 번 읽는 Python app은 credential 변경 후 rollout/restart하고, 동적 file rotation을 암묵적으로 기대하지 않는다.

Grafana Dashboard Importer처럼 VM에서 실행하는 Python app은 private `.env`를 사용할 수 있다. k3s에 배포하는 Python app은 같은 field contract를 Kubernetes Secret volume과 `secrets_dir`로 충족한다. Alloy credential은 Python settings를 통과시키지 않고 Alloy process에만 최소 권한으로 주입한다.

OCI registry credential은 application configuration이 아니다. kubelet이 image를 pull할 때만
사용하므로 Pydantic settings나 process Secret volume에 넣지 않는다. V2 base manifest는
강사가 `tta-aiqa` namespace에 사전 생성한 `ghcr-pull` `imagePullSecret`을 Risk API와
KServe Predictor에만 참조한다. 실제 registry token과 Secret manifest는 GitOps repository에
commit하지 않는다.

## 5. Apps

### 5-1. Data Quality Pipeline

`apps/data-quality-pipeline`은 PhysioNet source 검증, patient record 정규화, feature 집계, split, traffic pool 생성과 Great Expectations 검증을 실행한다.

```text
apps/data-quality-pipeline/
├── src/data_quality_pipeline/
│   ├── main.py
│   ├── bootstrap.py
│   ├── settings.py
│   └── adapters/inbound/cli.py
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
prepare    raw archive에서 patient-level dataset, split과 traffic pool 생성
validate   GE expectation과 checkpoint 실행
```

### 5-2. Model Trainer

`apps/model-trainer`는 baseline, Candidate A와 Candidate B model을 실제로 생성하고 MLflow에 기록한다.

```text
apps/model-trainer/
├── src/model_trainer/
│   ├── main.py
│   ├── bootstrap.py
│   ├── settings.py
│   └── adapters/inbound/cli.py
├── tests/
├── Dockerfile
└── pyproject.toml
```

강사 및 개발자용 `bootstrap` command는 세 model bundle을 만들고 baseline을 초기 deployed model로 publish한다.

### 5-3. Risk API

`apps/risk-api`는 deployed model을 읽어 온라인 추론을 제공한다.

```text
apps/risk-api/src/risk_api/
├── main.py
├── settings.py
├── bootstrap.py
└── adapters/
    ├── config.py
    ├── http.py
    ├── metadata.py
    ├── metric_labels.py
    └── telemetry.py
```

외부 REST, model metadata, metric label과 telemetry 계약은 Risk API가 소유한다.
Canonical input validation, scoring, label 결정과 event model은 `aiqa-serving` package가
소유하므로 Risk API에는 빈 domain/application/port 계층을 만들지 않는다. Compose에서는
local sklearn adapter를 사용하고 k3s에서는 내부 KServe endpoint를 호출하는 adapter를 사용한다.

```text
Compose  Risk API -> local sklearn adapter
k3s     Risk API -> internal KServe HTTP adapter
```

Endpoint 계약:

```text
GET  /health/live
GET  /health/ready
GET  /v1/model
POST /v1/predict
GET  /metrics
```

`POST /reload`와 `GET /events`가 필요한 경우 local diagnostics로만 제공하고 학생에게 공개하는 API 계약에는 포함하지 않는다. k3s의 model 변경은 Argo CD와 KServe rollout으로 수행한다.

### 5-4. KServe Predictor

`apps/kserve-predictor`는 approved local sklearn bundle을 KServe V2 inference
protocol로 노출하는 별도 process다. Pydantic V2 request/response DTO, HTTP
lifecycle와 predictor runtime settings만 소유하며 canonical feature validation과
scoring은 `aiqa-serving` function을 재사용한다.

```text
apps/kserve-predictor/src/kserve_predictor/
├── main.py
├── settings.py
├── bootstrap.py
└── adapters/
    ├── http.py
    └── kserve_v2.py
```

Risk API는 public course REST surface를, KServe Predictor는 internal model-serving
surface를 각각 소유한다. KServe Predictor는 별도 business policy를 만들지 않고
KServe V2 protocol을 `aiqa-serving`의 canonical scoring input/output으로 번역하므로
빈 domain/application/port 계층을 만들지 않는다. 두 app은 서로 import하지 않는다.

### 5-5. Traffic Generator

`apps/traffic-generator`는 API와 독립된 운영 traffic simulator다.

```text
apps/traffic-generator/src/traffic_generator/
├── main.py
├── settings.py
├── bootstrap.py
├── domain/
│   ├── scenarios.py
│   └── payloads.py
├── application/generate.py
├── ports/traffic.py
└── adapters/
    ├── config.py
    ├── csv_pool.py
    ├── http_client.py
    ├── jsonl.py
    └── wire_values.py
```

```text
baseline                평상시 입력과 기준 prediction 분포
current-shift           ICU type/measurement coverage 구성 변화와 positive risk 증가
validation-failure      null과 range 오류 요청
approved-candidate      Candidate B 배포 후 smoke와 운영 요청
```

Traffic은 고정 seed로 재현하고 client response와 server prediction event를 서로 다른 artifact로 관리한다.
Candidate A의 guardrail은 offline model evaluation에서 확인하므로 배포 traffic 대상에 포함하지 않는다. Traffic Generator는 scenario 규칙을 소유하므로 app 내부에 필요한 범위의 `domain`, `application`, `ports`, `adapters`를 둔다.

### 5-6. Grafana Dashboard Importer

`apps/grafana-dashboard-importer`는 dashboard template을 개인 stack 설정으로 변환하고 Grafana Cloud API에 idempotent하게 생성 또는 갱신하는 CLI app이다.

```text
apps/grafana-dashboard-importer/
├── src/grafana_dashboard_importer/
│   ├── main.py
│   ├── settings.py
│   ├── bootstrap.py
│   ├── domain/
│   │   ├── dashboard.py
│   │   └── bindings.py
│   ├── application/import_dashboard.py
│   ├── ports/dashboard_gateway.py
│   └── adapters/
│       ├── template.py
│       └── grafana_http.py
├── tests/
├── pyproject.toml
└── README.md
```

Domain은 versioned dashboard JSON의 datasource placeholder와 per-student UID binding을
순수 값과 함수로 소유한다. Application layer는 세 datasource 접근을 확인한 뒤 bound
dashboard를 idempotent gateway로 전달한다. Grafana Cloud HTTP 요청과 인증은 outbound
adapter만 담당하고 dashboard JSON은 structured data로 읽고 수정한다.

## 6. Packages

### 6-1. AIQA Core

- canonical feature name, dtype, nullability와 target 계약
- package 간 실제로 공유되는 순수 feature value

`aiqa-core`는 다른 AIQA package를 의존하지 않는다.
Model role, metadata, prediction result와 prediction event는 각각의 bounded context가
소유하며 core로 이동하지 않는다.

### 6-2. AIQA Data

- column과 label 표준화
- PhysioNet 환자별 raw record와 outcome join
- `-1` missing sentinel 정규화와 type/unit 변환
- 최초 48시간 measurement의 patient-level 집계와 missing indicator 생성
- available feature manifest, schema와 hash 생성
- patient 단위 stratified deterministic split
- operational traffic pool과 invalid request scenario 생성
- dataset manifest와 hash 생성

Model 학습과 prediction event 생성은 포함하지 않는다.

### 6-3. AIQA Model

- train 기반 feature diagnostics와 leakage 검사
- versioned feature subset 적용과 canonical model input contract 생성
- sklearn pipeline 생성
- 학습, scoring과 평가
- metric과 confusion matrix 계산
- threshold 평가
- model과 metadata 저장 및 로딩
- MLflow dataset/run/model logging
- baseline, Candidate A와 Candidate B 비교 결과 생성

Feature diagnostics에는 dtype, 결측률, 고유값, 분산, correlation, coefficient와 permutation importance 같은 내부 evidence 생성을 포함한다. Feature subset 비교는 Phase 0의 133개 전체 구성을 우선하며 상수, 전부 missing, 명확한 leakage 또는 재현성 문제를 제거하는 제한된 범위로 수행한다. CLI, sleep loop와 환경 변수는 포함하지 않는다.

### 6-4. AIQA Serving

- HTTP framework와 독립된 prediction use case
- scoring model protocol
- event sink protocol
- score, threshold와 label 결정
- prediction result 계약

FastAPI route와 Pydantic HTTP schema는 app이 소유한다.

### 6-5. AIQA Observability

- 모든 Python process의 execution context와 correlation ID
- JSON structured log formatting
- W3C trace 생성, child operation과 outbound propagation
- long-lived app이 명시적으로 선언한 bounded Prometheus metric registry
- FastAPI instrumentation과 lifespan bridge

`aiqa-observability`는 bounded context가 아닌 platform SDK다. prediction event, metric 이름·label·bucket, traffic scenario와 dashboard query는 각 app이 소유한다. SDK는 AIQA business package를 import하지 않으며, Grafana/Loki/Tempo SDK 또는 dashboard API도 포함하지 않는다. Runtime app은 log, metric과 trace를 표준 형식으로 노출하고 Alloy가 Grafana Cloud로 전달한다. Telemetry write credential은 Alloy 실행 환경에만 주입하고 dashboard API 호출은 Dashboard Importer app으로 격리한다.

### 6-6. AIQA QA

- data/model/deployment/operation evidence의 context-neutral summary
- evidence reference와 quality issue
- approval, conditional hold와 rollback policy
- `ReleaseDecision` 생성 use case
- owner, next action과 reevaluation condition 계약

`aiqa-qa`는 다른 bounded context의 entity를 직접 import하지 않는다. App 또는 Lab의 anti-corruption mapping을 통해 context별 output을 QA evidence DTO로 변환한다. 별도 `quality-gate` app은 우선 만들지 않고 5장 Lab과 pytest scenario test가 package use case를 호출한다.

### 6-7. Import 방향

```text
                         aiqa-core
                 ↑          ↑          ↑          ↑
            aiqa-data  aiqa-model  aiqa-serving  aiqa-qa
                 ↑          ↑          ↑          ↑
                 └── app composition roots and Labs ──┘

        aiqa-observability platform SDK
                 ↑ every Python process
```

각 bounded context package는 원칙적으로 `aiqa-core`만 의존한다. `aiqa-observability`는 business package를 import하지 않는 platform SDK이며 모든 app이 직접 의존한다. Context 간 변환과 조립은 app composition root 또는 Lab adapter에서 수행한다. Package는 app을 import하지 않고 app 간 Python import도 허용하지 않는다.

| Composition Root | 조립하는 Context |
| --- | --- |
| Data Quality Pipeline | Data Quality + Observability platform SDK |
| Model Trainer | Data Quality, Model Lifecycle + Observability platform SDK |
| Risk API | Model Lifecycle, Serving + Observability platform SDK |
| KServe Predictor | Serving + Observability platform SDK |
| Traffic Generator | Shared Kernel, HTTP client adapter + Observability platform SDK |
| Grafana Dashboard Importer | App-local import use case, Grafana Cloud HTTP adapter + Observability platform SDK |
| Release Decision Lab | Data Quality, Model Lifecycle, Release Assurance + Observability platform SDK |

## 7. Architecture와 Test 전략

### 7-1. 필수 Engineering 원칙

V2 구현은 Clean Architecture, Domain-Driven Design과 Test-Driven Development를 기본 개발 원칙으로 사용한다. 교육 시나리오와 end-to-end 조건도 동일한 pytest 기반 TDD 범위에서 구현한다.

- Domain은 framework, filesystem, network와 vendor SDK를 모른다.
- Dependency는 바깥 layer에서 안쪽 layer로만 향한다.
- Business 용어와 invariant는 bounded context가 소유한다.
- App은 use case를 조립하는 composition root와 delivery adapter를 담당한다.
- 모든 behavior 변경은 실패하는 test에서 시작한다.
- Architecture 규칙은 문서에만 두지 않고 자동 test로 검증한다.

### 7-2. Bounded Context와 Platform SDK

| Type | Package | 핵심 책임 |
| --- | --- | --- |
| Shared Kernel | `aiqa-core` | 최소 공통 value와 cross-context identifier |
| Bounded Context | `aiqa-data` | dataset snapshot, role, split, validation input과 lineage |
| Bounded Context | `aiqa-model` | training, evaluation, candidate와 model publication |
| Bounded Context | `aiqa-serving` | prediction use case, scoring contract와 result |
| Bounded Context | `aiqa-qa` | evidence, approval policy와 release decision |
| Platform SDK | `aiqa-observability` | execution context, JSON log, trace propagation과 bounded metric registry |

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
CandidateId
ModelCandidate
PublishedModel
PredictionRequest
PredictionResult
PredictionEvent
EvidenceReference
QualityIssue
ReleaseStatus
ReleaseDecision
```

Candidate A와 Candidate B는 동일한 `candidate` role을 가지며 `CandidateId`로 구분한다. `ReleaseStatus`는 최소 `HOLD`와 `APPROVE`를 표현한다. `baseline`, `candidate`, `deployed`, `label`, `score`, `threshold`, `prediction`을 서로 바꾸어 쓰지 않는다. 용어 의미가 바뀌는 결정은 `docs/adr/`에 기록한다.

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

App의 `main.py`는 process entry point, `bootstrap.py`는 composition root, `adapters/inbound`는 HTTP 또는 CLI delivery를 담당한다. 외부 연동 구현은 `adapters/outbound`에 둔다. Traffic Generator처럼 app 자체가 고유한 scenario behavior를 소유할 때만 app 내부에 `domain`, `application`과 `ports`를 추가한다.

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
6. architecture test와 관련 scenario test 재실행
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
| Characterization | root `tests/characterization` | AS-IS 데이터, API, model과 telemetry 계약 |
| Scenario | root `tests/scenarios` | 두 candidate 판단과 교육 사건의 연결 결과 |
| End-to-End | root `tests/e2e` | DVC, app, Compose, k3s와 telemetry 흐름 |

Unit test는 작고 빠르며 network와 Docker 없이 실행되어야 한다. Full PhysioNet archive 대신 최소 patient-record fixture를 사용하고 데이터 전체 재현은 integration/e2e로 제한한다.

### 7-10. Scenario Test 범위

교육 사건은 pytest scenario test로 고정한다. Scenario test는 여러 bounded context와 app이 연결된 결과를 검증하고 개별 함수 동작은 package unit test에서 다룬다.

```text
tests/scenarios/
├── test_candidate_decisions.py
├── test_baseline_serving.py
├── test_approved_candidate_deployment.py
├── test_operational_shift.py
├── test_dashboard_import_and_accumulation.py
├── test_release_decision.py
└── test_rollback_path.py
```

### 7-11. 핵심 Scenario Test

`test_candidate_decisions.py`는 동일한 data revision과 test dataset으로 평가한 세 model에 다음 결과가 나오는지 검증한다.

이 target scenario test는 Phase 0의 F2가 train/valid에서 성립한 뒤에만 고정한다. Feasibility 이전에는 model 결과를 test fixture나 하드코딩 metric으로 만들어 통과시키지 않는다.

- Candidate A의 Precision 개선 여부와 별개로 Recall 또는 guardrail 미충족 시 `HOLD`가 생성됨
- Candidate B가 필수 metric과 guardrail을 모두 만족하면 `APPROVE`가 생성됨
- 승인 규칙은 test 안에서 다시 계산하지 않고 `aiqa-qa`의 release evaluation use case 결과로 검증함

추가 scenario test는 다음 behavior를 고정한다.

- PhysioNet raw의 missing sentinel, 불규칙 측정과 실제 outlier가 품질 evidence로 기록됨
- Patient-level processed dataset이 model readiness contract를 충족함
- VM 시작 상태에서 baseline model이 같은 API URL로 응답함
- Candidate A는 배포 대상 manifest로 선택되지 않음
- Candidate B 배포 후 model version과 telemetry label이 함께 바뀜
- Current-shift traffic 후 positive mortality-risk rate가 baseline 범위를 벗어남
- Invalid traffic이 API error rate와 validation event를 증가시킴
- 개인 Grafana Cloud dashboard import가 고정 UID로 생성 또는 갱신되고 traffic 후 새 telemetry를 조회함
- Rollback smoke test 후 baseline model version과 health가 복구됨

### 7-12. Test 실행 계층

```bash
uv run pytest -m "not integration and not e2e"
uv run pytest -m integration
uv run pytest tests/scenarios
uv run pytest -m e2e
```

Docker, k3s 또는 외부 URL이 필요한 test는 marker로 분리한다. Test coverage는 품질 guardrail로 사용하되 숫자 자체를 목표로 삼지 않고 domain invariant와 application branch의 누락을 우선 검토한다.

Root dev dependency에는 pytest와 coverage 측정 도구를 두고 app/package가 별도 test runner를 만들지 않는다. Pytest marker는 `integration`, `e2e`, `requires_docker`, `requires_k3s` 실행 범위를 통제한다.

### 7-13. Configuration Test

Configuration 변경도 behavior 변경으로 취급하고 실패 test에서 시작한다.

- 각 YAML의 `schema_version`, required field, type과 range를 검증한다.
- `physionet-record.yaml`의 parameter, unit, sentinel과 `aggregation.yaml`의 output feature가 일관되는지 검증한다.
- `model-input.yaml`의 feature 순서, target과 label이 Data, Model과 Serving에서 동일한 typed contract로 해석되는지 검증한다.
- 중복 feature, target의 feature 포함, unknown key와 비어 있는 profile을 거부한다.
- Candidate A/B profile ID와 release policy가 서로 참조 가능한지 검증한다.
- Threshold, split ratio, traffic weight와 latency limit의 허용 범위를 검증한다.
- Dashboard JSON이 요구하는 datasource placeholder와 telemetry label을 참조하는지 검증한다.
- Config hash가 model metadata, MLflow run과 release evidence에 기록되는지 integration test로 검증한다.
- Secret 또는 실제 endpoint가 tracked configuration에 포함되지 않는지 검사한다.
- App별 `BaseSettings`가 environment, `.env`와 secrets directory에서 같은 field contract를 해석하는지 검증한다.
- Settings field alias와 Kubernetes Secret key/file name이 일치하는지 manifest contract test로 검증한다.
- 필수 runtime setting 또는 Secret이 없거나 잘못된 type이면 process 시작 단계에서 fail-fast하는지 검증한다.
- Domain과 application layer가 `pydantic-settings`, environment와 Secret path를 직접 참조하지 않는지 architecture test로 검증한다.

## 8. 데이터 설계

### 8-1. 원본 데이터

V2 기준 데이터는 PhysioNet의 `Predicting Mortality of ICU Patients: The PhysioNet/Computing in Cardiology Challenge 2012` Version 1.0.0 Set A다.

- Source: `https://physionet.org/content/challenge-2012/1.0.0/`
- DOI와 citation은 `data/README.md`와 dataset manifest에 기록한다.
- Access policy는 open access이며 file license는 Open Data Commons Attribution License v1.0이다.
- Set A는 outcome이 공개된 ICU stay 4,000건으로 구성된다.
- 환자별 최초 48시간 동안 최대 42개 descriptor/measurement가 기록된다.
- `set-a.zip`은 약 7.6MB이고 `Outcomes-a.txt`는 약 77KB다.

```text
data/raw/physionet-2012/
├── set-a.zip
├── Outcomes-a.txt
├── LICENSE.txt
└── source-manifest.yaml
```

수강생 VM의 네트워크 상태와 무관하게 재현할 수 있도록 작은 공식 원본 archive, outcome, license와 checksum manifest를 Git에서 관리한다. `source-manifest.yaml`에는 source URL, version, retrieval date, SHA-256, license와 citation을 기록한다. 기존 Kaggle `human_vital_signs_dataset_2024.csv`는 V2 active data에서 제거하고 legacy 참고 자료로만 남긴다.

### 8-2. Raw Grain과 실제 품질 특성

각 ICU stay는 하나의 raw record file이고 각 행은 `Time`, `Parameter`, `Value` measurement다. 동일 환자에서 변수별 측정 횟수와 시점이 다르며 일부 변수는 한 번도 측정되지 않는다. `-1`은 missing/unknown sentinel이고 실제 outlier와 서로 다른 sensor 방식의 혈압 측정이 존재할 수 있다.

이 특성을 그대로 품질 학습 근거로 사용한다.

- 환자 record/file 누락과 outcome join coverage
- patient identifier uniqueness
- 최초 48시간 timestamp parsing, 범위와 정렬
- variable별 measurement coverage와 missing ratio
- `-1` sentinel의 null normalization
- 중복 또는 근접 시점 measurement
- 생리적으로 의심스러운 outlier와 단위
- ICU type과 target class 분포

임의 null, range 또는 label flip을 주입한 `valid_degraded`는 만들지 않는다. Source에서 실제 관측되는 품질 문제와 raw-to-processed 변환 전후를 비교한다.

### 8-3. Patient-Level Dataset 생성

Data Quality Pipeline은 다음 순서로 patient-level dataset을 생성한다.

```text
공식 archive/checksum 검증
  -> 환자별 raw record parse
  -> -1 sentinel을 null로 normalize
  -> Outcomes-a.txt를 RecordID로 join
  -> 최초 48시간 measurement를 변수별 count/min/max/mean/latest로 aggregate
  -> measurement coverage와 missing indicator 생성
  -> patient-level feature table과 manifest 생성
```

Aggregation 대상, 단위와 허용 범위는 versioned config에서 관리한다. Imputer, scaler, encoder와 feature selection은 sklearn pipeline에 포함하고 train split에만 fit한다. Outcome, SAPS-I, SOFA와 입원 이후 결과에서 파생되는 값이 model feature로 유입되지 않도록 leakage test를 둔다.

Phase 2의 patient-level table은 Phase 0에서 검증한 133개 available feature를 v1 data contract로 재현한다. 이 table은 model input의 상한이며 세 model이 실제로 사용할 canonical subset과 순서는 Phase 4 내부 준비 과정에서 test를 열기 전에 별도로 동결한다.

### 8-4. Patient-Level Split

4,000 ICU stay를 `RecordID` 단위로 분리하고 target 비율을 유지하는 deterministic stratified split을 사용한다. 기본 seed는 `42`이며 정확한 class count는 pipeline 실행 결과를 manifest에 기록한다.

| Dataset | 비율 | 예상 ICU stay | 역할 |
| --- | ---: | ---: | --- |
| `train` | 60% | 2,400 | 세 model pipeline 학습과 cross-validation |
| `valid` | 15% | 600 | model profile, threshold와 release 후보 선택 |
| `test` | 15% | 600 | 선택 완료 후 세 model 공통 최종 평가 1회 |
| `release_holdout` | 10% | 400 | API regression, baseline/current traffic과 rollback 확인 |

Model profile, preprocessing parameter와 threshold는 `train`과 `valid`만 사용해 확정한다. `test` 결과를 확인한 뒤 profile이나 release policy를 조정하지 않는다. `release_holdout`의 label은 traffic payload에 포함하지 않으며 학습, model 선택과 threshold tuning에 사용하지 않는다.

### 8-5. Data Lineage

```text
PhysioNet Set A + Outcomes A
  -> normalized patient measurements
  -> patient-level aggregate dataset
      ├── train ──────────────→ baseline/Candidate A/Candidate B
      ├── valid ──────────────→ profile와 threshold 선택
      ├── test ───────────────→ 공통 최종 metric
      └── release_holdout
          ├── baseline sample ─→ baseline traffic
          ├── shifted sample ──→ current-shift traffic
          └── mutated payload ─→ invalid traffic
```

## 9. DVC, Great Expectations와 MLflow

### 9-1. DVC 범위

DVC는 데이터 version과 data pipeline만 담당한다. Remote 없이 local cache를 사용하며 원본은 Git에서 가져온다.

```text
dvc.yaml
├── verify-source
├── extract
├── normalize
├── aggregate
├── split
└── operational
```

`params.yaml`은 48시간 observation window, aggregation, split ratio와 seed를 관리한다. `dvc.lock`은 stage command와 input/output hash를 기록한다.

DVC stage는 실제 사용하는 설정만 dependency로 선언한다. `verify-source`, `normalize`와 `aggregate`는 `physionet-record.yaml`과 `aggregation.yaml`에 의존하고, `split`은 split parameter에 의존하며, `operational`은 동결된 model input과 traffic scenario가 필요한 시점에만 해당 config를 의존한다. 아직 확정되지 않은 canonical `model-input.yaml` 때문에 available feature dataset이 불필요하게 다시 생성되지 않도록 stage 경계를 유지한다. 설정 변경으로 output이 달라지면 `dvc.lock`과 config hash가 함께 변경되어야 한다.

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

교육 흐름에서는 Notebook과 Pandas로 PhysioNet raw record의 missing sentinel, measurement coverage, 불규칙 시점과 outlier를 직접 EDA한 뒤 같은 확인 항목을 Great Expectations로 자동화한다. GE 실행은 DVC data stage와 분리하며 V2에서는 training dataset publish를 차단하는 gate로 사용하지 않는다.

- raw ingestion expectation suite와 checkpoint
- processed model-readiness expectation suite와 checkpoint
- raw record schema, parameter vocabulary, timestamp, sentinel, range와 identifier 검사
- patient-level feature schema, outcome join, null policy, row count와 split overlap 검사
- Validation Result와 Data Docs 생성
- raw에서 발견한 실제 품질 신호와 processed readiness 개선을 전후 evidence로 비교
- 실행 결과가 기대와 다르면 command가 non-zero exit code를 반환

Raw outlier와 missing record는 원본에서 삭제하지 않는다. Preprocessing decision, 제외/보정 row와 aggregation 결과는 manifest로 추적한다. API invalid request는 데이터셋 품질 검증과 분리된 serving contract scenario로만 생성한다.

### 9-3. MLflow 범위

MLflow는 model experiment와 artifact의 기준 저장소다.

- local SQLite backend
- local filesystem artifact store
- baseline, Candidate A와 Candidate B run
- dataset name, source, digest와 context
- model parameters, threshold와 metric
- model artifact와 metadata

각 run에는 다음 provenance를 기록한다.

```text
git_commit
dvc_lock_revision
raw_data_hash
train_data_hash
valid_data_hash
test_data_hash
split_seed
model_profile
threshold
model_input_config_hash
model_profile_config_hash
evaluation_config_hash
```

Release decision evidence에는 위 provenance와 함께 `release_policy_config_hash`를 기록한다. Model bundle의 metadata에는 resolved feature contract와 model profile snapshot을 포함한다.

### 9-4. 도구 책임 구분

```text
DVC                 어떤 데이터와 pipeline revision인가
Great Expectations  데이터가 어떤 규칙을 통과하거나 실패했는가
MLflow              그 데이터로 어떤 model과 metric을 만들었는가
```

### 9-5. Artifact Identity와 Release Provenance

해시는 모든 Python 파일을 나열하기 위한 장치가 아니다. 각 artifact가 다른
책임 경계로 넘어갈 때 immutable reference를 연결하기 위한 값이다. Source code와
versioned config의 기준은 clean Git commit이며, module별 SHA-256 목록을 freeze에
유지하지 않는다.

| 질문 | 기준 reference | 교육에서 설명하는 이유 |
| --- | --- | --- |
| 어떤 code/config인가 | Git commit과 `uv.lock` | 같은 source와 dependency 정의에서 실행했는지 확인한다. |
| 어떤 data인가 | `dvc.lock`, source manifest, split role dataset digest | 재현한 pipeline과 sealed test CSV를 식별한다. |
| 어떤 model인가 | MLflow run ID, logged artifact, model/metadata digest, feature contract digest | metric, 입력 계약과 serialized bundle을 연결한다. |
| 무엇을 승인했는가 | pre-test `release-freeze.json`, post-test `release-manifest.json` | test 전 동결과 test 후 release 결정을 분리한다. |
| 무엇이 실제 실행되는가 | OCI image digest, immutable PVC model path, expected model digest | mutable tag나 바뀐 mounted file을 배포 identity로 오인하지 않는다. |

`release-freeze.json`은 bundle 생성 뒤와 sealed test 전 사이에 작성한다. Git
commit, DVC/data-lineage reference, `test.csv` digest, model/metadata digest,
feature/profile/evaluation/release-policy config digest와 MLflow run ID를 포함한다.
Final evaluation은 이를 검증한 뒤에만 test와 bundle을 연다.

`release-manifest.json`은 final decision 뒤에 생성한다. freeze manifest digest,
canonical evidence digest, approved profile, MLflow run ID와 approved model digest를
연결한다. 이는 SLSA provenance의 artifact/dependency 연결 방식을 참고한 교육용
release record이며, trusted builder와 서명이 없는 현재 환경을 SLSA compliant라고
표현하지 않는다.

MLflow Tracking은 필수이며 Model Registry version, tag와 alias는 강사용 release
control로만 선택 도입한다. Alias는 mutable하므로 GitOps deployment에는 resolved
model version과 immutable digest를 기록한다. KServe predictor는 startup에서
expected model digest를 검증하고, 일치할 때만 ready를 반환한다.

Great Expectations result는 data identity나 publish permission이 아니다. V2에서는
EDA를 자동화한 quality evidence로 남기며, block/notify 정책은 별도 운영 결정으로
둔다. Custom Traffic Generator는 feature shift와 invalid request라는 domain scenario를
만들고, k6는 강사용 smoke/load 검증에서 VU, arrival rate와 threshold를 담당한다.

표준 reference와 대안 선택 이유는
[ADR 0006](adr/0006-layered-artifact-identity-and-release-provenance.md)에 기록한다.

## 10. Baseline과 두 Candidate Model

### 10-1. Baseline Feasibility

가장 먼저 target prevalence를 그대로 예측하는 `DummyClassifier`와 단순하고 해석 가능한 sklearn pipeline을 비교한다. 첫 non-trivial baseline은 imputation, missing indicator, scaling/encoding과 선형 분류기를 기본 후보로 두되 benchmark 결과에 따라 model family를 확정한다.

Baseline feasibility는 다음 evidence를 요구한다.

- Patient-level split의 class support와 fold별 positive count
- Dummy의 Precision, Recall, F1, AUROC와 PR-AUC
- Stratified repeated cross-validation의 mean, dispersion과 fold별 confusion matrix
- Non-trivial baseline의 PR-AUC가 target prevalence/Dummy보다 일관되게 나은지 여부
- Score가 상수가 아니며 threshold 변화에 따른 Precision/Recall trade-off가 존재하는지 여부
- Missingness만으로 target을 사실상 복원하는 shortcut이 없는지 여부
- Feature importance/coefficient가 post-outcome 또는 identifier leakage를 가리키지 않는지 여부

정확한 feasibility margin과 반복 횟수는 `configs/model/evaluation.yaml`에 먼저 기록하고 final test를 열기 전에 freeze한다. Small sample의 불확실성을 숨기지 않고 fold 분산, positive support와 bootstrap confidence interval을 교육 evidence에 포함한다.

`Outcomes-a.txt`에서는 `RecordID`와 `In-hospital_death`만 join에 사용한다. `SAPS-I`, `SOFA`, `Length_of_stay`와 `Survival`은 outcome-side descriptor이므로 model feature, imputation과 feature selection 입력에서 금지하고 leakage test로 강제한다.

### 10-2. 내부 Feature Preparation과 Bootstrap

Baseline과 두 candidate 생성 과정은 repository 내부 구현이며 강의 내용에서 feature 탐색, selection과 profile 탐색 과정을 설명하지 않는다.

```bash
uv run python scripts/run_model.py bootstrap
```

내부 bootstrap은 다음 순서로 실행한다.

```text
133개 available feature manifest 확인
  -> train 기반 feature diagnostics 생성
  -> versioned feature set을 train repeated-CV로 비교
  -> 유망한 소수만 valid에서 확인
  -> canonical model input, model profile과 threshold 동결
  -> 세 model bundle과 MLflow run 생성
  -> sealed test 공통 평가 1회
```

Feature set은 기본적으로 Phase 0의 133개 전체 구성을 사용한다. 시나리오에 맞는 숫자를 만들기 위한 광범위한 feature 탐색은 하지 않으며, subset 검토가 필요하면 `full`, `quality-filtered`, `reduced`처럼 사전에 이름 붙인 제한된 profile만 versioned config로 비교한다. 상세 correlation, importance와 fold diagnostics는 generated artifact로 두고 선택 이유, config hash와 최종 manifest만 prepared evidence로 보존한다.

```text
artifacts/models/
├── baseline/
│   ├── model.joblib
│   └── metadata.json
├── candidate-a/
│   ├── model.joblib
│   └── metadata.json
├── candidate-b/
│   ├── model.joblib
│   └── metadata.json
└── deployed/
    ├── model.joblib
    └── metadata.json
```

### 10-3. Model 계약

- Baseline, Candidate A와 Candidate B는 서로 다른 실제 model bundle이다.
- 세 모델은 같은 train/valid/test 계약을 사용한다.
- Candidate A는 Precision 중심 profile이며 Recall 또는 guardrail 미충족 `HOLD`를 목표로 한다.
- Candidate B는 균형 profile이며 필수 release 기준을 충족하는 `APPROVE`를 목표로 한다.
- Candidate A와 Candidate B의 `ModelRole`은 모두 `candidate`이고 별도 candidate identifier로 구분한다. 이름에 승인 결과를 저장하지 않는다.
- Profile과 threshold 선택에는 `train`과 `valid`만 사용하고 `test`는 선택 완료 후 공통 최종 평가에 한 번 사용한다.
- Model bundle에는 학습 시점의 resolved `FeatureSet`, label contract와 config hash를 포함한다.
- Serving은 현재 input contract와 model bundle의 contract hash가 다르면 시작을 거부한다. 배포 시에는 approved model digest도 함께 검증하며 file reload로 model을 교체하지 않는다.
- Metric과 prediction rate는 실제 prediction으로 계산한다.
- 목표 숫자를 JSON에 하드코딩하지 않는다.
- Scenario test는 정확한 한 값보다 방향과 허용 범위를 검증한다.
- 초기 `deployed` model은 baseline이다.
- Canonical benchmark가 `APPROVE`를 생성한 경우에만 `deployed` model을 Candidate B로 바꾸며 Candidate A는 배포 대상이 아니다.

### 10-4. Metric 책임

- Precision, Recall, F1과 confusion matrix는 model evaluation에서 계산한다.
- positive mortality-risk prediction rate는 model output과 traffic 구성에서 계산한다.
- API error rate는 invalid traffic과 HTTP response에서 계산한다.
- Latency는 실행 환경 영향을 받으므로 baseline 대비 변화와 limit으로 판단한다.

### 10-5. Metric과 Release Policy Calibration

사망 554건의 불균형과 small sample을 고려해 model ranking metric과 운영 decision metric을 분리한다.

| 목적 | Metric | 사용 방식 |
| --- | --- | --- |
| Predictive signal | PR-AUC, AUROC | Dummy/prevalence 대비 ranking signal과 cross-validation 안정성 확인 |
| Operating point | Precision, Recall, F1 | Valid에서 threshold를 선택하고 실제 trade-off 설명 |
| 환자 영향 | TP, FP, FN, TN | 비율과 함께 실제 건수 및 positive support 표시 |
| 불확실성 | fold dispersion, bootstrap CI | 작은 test에서 미세 차이를 과대 해석하지 않음 |
| 운영 품질 | latency, error rate, positive prediction rate | Offline model metric과 분리해 배포 후 관측 |

Release policy는 임상 기준이라고 부르지 않고 교육용 운영 guardrail로 명시한다. Candidate B는 Recall/FN guardrail을 충족하면서 Precision이 허용 범위 아래로 무너지지 않아야 한다. Candidate A는 더 높은 Precision을 보일 수 있지만 Recall 또는 FN guardrail을 위반하는 profile을 목표로 한다. PR-AUC/AUROC가 baseline보다 나쁘거나 confidence interval이 과도하게 겹치는 경우 threshold metric만으로 개선을 주장하지 않는다.

정확한 threshold와 guardrail 수치는 train cross-validation과 valid 결과를 바탕으로 `release-policy.yaml`에 freeze하고 test 전 commit한다. Test support가 작으므로 1~2건 차이 또는 반올림 차이로 승인 상태가 뒤집히는 정책을 사용하지 않는다. Clinical utility, 환자 치료 결정과 실제 병원 배포 적합성은 평가 범위 밖이다.

### 10-6. Canonical Benchmark와 교육 수치

계획 단계에서 임의 metric과 threshold를 확정하지 않는다. Data/Model 구현 후 고정된 PhysioNet source checksum, split seed, feature contract와 세 model profile로 canonical benchmark를 실행한다.

```text
train + cross-validation
  -> model family와 preprocessing 후보 탐색
valid
  -> Baseline/Candidate A/Candidate B profile과 threshold 확정
  -> release policy freeze
test
  -> 세 model 공통 최종 평가 1회
  -> canonical benchmark evidence 생성
  -> 교재와 dashboard 기준값 갱신
```

Canonical evidence는 다음을 포함한다.

```text
docs/reference/evidence/model-evaluation/
├── benchmark-manifest.json
├── baseline.json
├── candidate-a.json
├── candidate-b.json
└── comparison.json
```

- Source/DVC/config/code hash와 sklearn version
- Split별 row count, positive support와 class ratio
- Algorithm, preprocessing, hyperparameter와 threshold
- Precision, Recall, F1, AUROC, PR-AUC와 positive prediction rate
- TP, FP, FN, TN confusion matrix
- Valid cross-validation summary와 final test result 구분
- Release policy evaluation과 `HOLD`/`APPROVE` 근거

`ttamlops-2607`의 표, 예시 output, release report와 dashboard reference는 이 evidence의 실제 수치로 갱신한다. 코드에서 문서 숫자를 역으로 맞추지 않으며 test 결과를 본 뒤 release threshold를 완화하지 않는다. Source, split, feature, profile 또는 dependency가 바뀌면 benchmark revision을 새로 생성하고 영향받는 교재 수치를 함께 갱신한다. Docs consistency test는 교재에 노출된 canonical 숫자가 benchmark manifest와 일치하는지 검증한다.

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

### 11-2. 강사가 제공하는 실습 URL 수

과거 `tmp/legacy/domains.csv`에는 30개 VM과 학생별 app/MLflow hostname이 각각 두 계열씩 정의되어 있다. V2에서는 학생에게 하나의 canonical 계열만 안내한다.

학생별 VM에 연결되는 전용 hostname은 2개다.

| 서비스 | 개수 | 역할 |
| --- | ---: | --- |
| Risk API | 1 | `/docs`, `/health`, `/predict`, `/metrics`; KServe는 cluster 내부 서비스 |
| MLflow | 1 | run, metric, dataset과 model artifact |

강사가 제공하는 공용 hostname은 Argo CD 1개다.

| 서비스 | 개수 | 구분 방식 |
| --- | ---: | --- |
| Argo CD | 1 | 학생별 Application과 RBAC |

교재 사이트 URL은 별도 공용 링크다. 한 학생이 강사에게 받는 정보는 다음으로 제한한다.

```text
VS Code SSH alias 1개
개인 API URL 1개
개인 MLflow URL 1개
공용 Argo CD URL 1개
교재 URL 1개
```

Grafana Cloud URL과 credential은 강사가 제공하지 않는다. 각 수강생이 자신의 Grafana Cloud account와 stack을 만들고 개인 URL, telemetry write credential과 dashboard write token을 발급한다. 이 URL은 강사가 제공하는 개인 URL 2개에 포함하지 않는다.

### 11-3. URL 정책

- Baseline과 승인된 Candidate B는 같은 API URL을 사용한다.
- Candidate B 배포와 rollback smoke test 후 `model_version`이 바뀌는지 확인한다.
- API docs, health와 metrics는 별도 domain이 아니라 path로 제공한다.
- `homelab` 계열 hostname과 SSH stream port는 학생 문서에서 숨긴다.
- 실제 hostname은 repository에 하드코딩하지 않고 환경별 value로 주입한다.
- Course 문서는 “강사가 제공한 URL”로 표현한다.
- Grafana 화면은 “자신의 Grafana Cloud URL”로 표현한다.

### 11-4. Telemetry 구분

모든 log, metric과 trace에 다음 label을 공통으로 둔다.

```text
service
environment
model_role
model_version
model_run_id
```

각 수강생의 Grafana Cloud stack이 독립된 격리 경계다. Repository는 dashboard server나 telemetry backend를 배포하지 않으며 수강생은 repository의 dashboard template을 자신의 stack에 직접 import한다.

```text
Risk API log / metrics / OTLP
  -> Alloy
  -> 개인 Grafana Cloud stack
  -> 개인 dashboard query
```

Grafana Cloud 내부의 Loki, metrics backend와 Tempo를 직접 설치하거나 운영하는 과정은 교재에서 다루지 않는다.

개인 dashboard import 계약은 다음과 같다.

- Dashboard UID는 개인 stack 안에서 고정된 `aiqa-quality`를 사용한다.
- Dashboard title은 `AI Quality`를 사용한다.
- 같은 stack에서 다시 실행하면 새 dashboard를 중복 생성하지 않고 기존 dashboard를 갱신한다.
- Importer는 생성 또는 갱신된 dashboard URL을 출력한다.
- Grafana Cloud URL, dashboard write token, folder UID와 datasource UID는 환경 변수로 주입한다.
- Dashboard write token과 Alloy telemetry write token은 분리하고 Git에 저장하지 않는다.

Dashboard에는 최소한 request rate, error rate, latency, positive mortality-risk rate, score/prediction distribution, input missing indicator, recent logs와 trace 탐색 연결을 포함한다. Baseline telemetry가 먼저 보이고 Candidate B 배포와 traffic 실행 후 같은 dashboard에 새 model version의 데이터가 누적되어야 한다.

## 12. 배포 구조

### 12-1. Compose

Compose는 강사 검증, app별 local smoke test와 Docker 개념 실습에 사용한다.

```text
core profile
  MLflow, trainer, API, traffic

observability profile
  Alloy를 Grafana Cloud telemetry endpoint에 연결
```

Compose와 k3s에는 Grafana, Loki, Tempo와 Prometheus server를 추가하지 않는다. Local에서는 JSONL, `/metrics`와 trace payload를 직접 확인할 수 있고, 통합 환경에서는 Alloy가 이를 Grafana Cloud로 전달한다.

교육에서는 Compose의 Risk API와 Alloy를 먼저 실행해 local sklearn adapter, container log, Risk API service metrics와 OTLP 흐름을 확인한다. traffic process도 같은 SDK로 run context와 trace를 남긴다. 이후 동일한 Risk API application을 Kubernetes로 옮기고 model adapter를 KServe HTTP로 교체한다. Risk API와 KServe predictor는 W3C trace context와 request ID를 전달하며, Alloy discovery는 개별 service 이름이 아닌 AIQA workload label을 기준으로 동작한다.

```text
Compose     Traffic -> Risk API -> Local sklearn adapter
                        -> Compose Alloy -> Grafana Cloud

Kubernetes Traffic -> Risk API -> KServe HTTP adapter
                        -> Kubernetes Alloy -> Grafana Cloud
```

### 12-2. Kubernetes와 Argo CD

수강생 VM의 k3s에는 baseline model이 이미 배포되어 있다. 수강생은 manifest와 live state를 확인하고 승인된 Candidate B 변경을 GitOps로 반영한다.

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
- 외부 요청은 Risk API가 받고 내부 KServe endpoint를 `ScoringModel` adapter로 호출한다.
- Compose의 local sklearn adapter와 k3s의 KServe HTTP adapter는 같은 serving port를 구현한다.
- MLflow에서 승인된 model bundle은 publish adapter가 VM의 course model PVC에 content-addressed 경로로 복사한다. Custom KServe predictor는 `InferenceService`의 read-only PVC `subPath`로 이를 mount하며, ConfigMap의 expected model digest와 실제 bundle을 비교한다. 이 과정은 KServe `storageUri`에 의존하지 않는다.
- Candidate A는 KServe manifest에 반영하지 않고 Candidate B만 승인 후 배포한다.
- 환경이 준비되면 live `InferenceService`와 endpoint를 확인한다.
- 실행이 불가능한 경우 manifest inspection과 prepared evidence로 범위를 제한한다.
- Argo CD와 KServe를 별도 신규 교시로 만들지 않는다.

## 13. 교육 진행

### 13-1. 1일차

| 교시 | 기존 커리큘럼 | V2 실습 연결 |
| --- | --- | --- |
| 1교시 | AI 품질의 개요 | baseline과 두 candidate 운영 사건 소개 |
| 2교시 | 데이터 품질의 중요성 | development/operational 데이터 역할 구분 |
| 3교시 | 데이터 품질 확인 실습 | Notebook과 Pandas EDA |
| 4교시 | 데이터 검증 자동화 | PhysioNet raw/processed 확인 항목을 GE 검증으로 자동화 |
| 5교시 | 모델 품질 지표 이해 | Precision, Recall, F1, FP/FN, AUROC, PR-AUC와 threshold |
| 6교시 | 모델 성능 평가 실습 | 실제 baseline, Candidate A와 Candidate B 공통 test 비교 |
| 7교시 | 모델 실험 관리 | DVC revision과 MLflow run 연결 |

DVC는 7교시의 “데이터셋 변경에 따른 성능 변화 추적”을 구체화하며 별도 교시를 추가하지 않는다. 임의 degraded dataset을 만들지 않고 source/aggregation/split config revision과 MLflow run의 dataset digest를 연결해 어떤 데이터 처리 revision에서 metric이 생성되었는지 추적한다.

### 13-2. 2일차

| 교시 | 기존 커리큘럼 | V2 실습 연결 |
| --- | --- | --- |
| 1교시 | 컨테이너와 모델 서빙 | trainer/API container와 artifact 분리 |
| 2교시 | API 구성 | FastAPI contract, model version과 correlation ID |
| 3교시 | Kubernetes 기본 | Pod, Deployment, ConfigMap과 manifest |
| 4교시 | 모델 배포 실습 | baseline 상태와 승인된 Candidate B GitOps sync |
| 5교시 | 운영 품질의 위협 요인 | current-shift와 invalid traffic |
| 6교시 | 로그와 지표의 수집 | JSONL, `/metrics`, OTLP와 Alloy 연결 |
| 7교시 | Dashboard와 이상 대응 | Dashboard import, telemetry 누적 비교와 유지/보류/되돌림 판단 |

### 13-3. 수강생에게 노출하는 것

- VS Code Remote-SSH 접속
- Notebook EDA
- DVC revision과 DAG
- GE expectation과 Validation Result
- baseline과 두 candidate metric, release decision과 MLflow UI
- Dockerfile, API와 Kubernetes manifest
- Argo CD diff, sync와 resource health
- Grafana Cloud dashboard import와 traffic 실행 후 데이터 누적 확인
- 품질 이상 원인 후보와 대응 판단

### 13-4. 내부 코드로만 제공하는 것

- snapshot과 split 구현 세부사항
- Feature diagnostics, correlation, importance와 subset 비교
- Available feature에서 canonical model input을 동결하는 과정
- baseline과 두 candidate profile 탐색
- Train/valid에서 Candidate A/B의 의도한 metric 관계를 만족하는 실제 profile 선정
- prepared evidence 생성
- traffic 분포 조정 알고리즘
- VM provisioning과 실제 domain inventory

## 14. 실행 Workflow

### 14-1. 강사 및 개발자 준비

```bash
uv sync --all-packages --group notebook
uv run python scripts/setup_course.py
```

`setup_course.py`는 수강생 VM의 active data workspace를 준비하고 provisioned
baseline 시작 상태를 확인하는 내부 wrapper다. historical V2 evidence와 sealed-test
결과는 읽기 전용으로만 확인하며 재생성하지 않는다.

```text
notebook runtime 확인
  -> active DVC data pipeline 실행: source 검증, aggregate, split과 traffic pool 생성
  -> GE raw/processed validation artifact 생성
  -> V2 canonical decision과 provisioned baseline metadata 확인
```

### 14-2. 수강생 시작 상태

- Repository와 dependency 준비 완료
- DVC output과 GE evidence 준비 완료
- Baseline, Candidate A와 Candidate B MLflow run 준비 완료
- Baseline model 배포와 API health 정상
- Local baseline traffic과 telemetry fixture 준비 완료
- Alloy config example과 dashboard template 준비 완료

강사용 setup은 환경 이상을 미리 확인하기 위해 GE evidence와 local baseline telemetry를 생성해 둔다. 개인 Grafana Cloud 연결과 dashboard는 준비하지 않는다. 수강생은 1일차에 EDA 후 GE command를 다시 실행하고 2일차에 개인 Grafana Cloud 가입, credential 설정, Alloy 연결과 dashboard import를 직접 수행한다.

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

### 14-4. Grafana Cloud Dashboard 실습

수강생은 개인 Grafana Cloud stack에서 logs, metrics와 traces write endpoint, Alloy용 token, dashboard write token과 datasource UID를 확인해 private `.env`에 설정한다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

Alloy 연결 후 baseline traffic을 실행하고 Importer가 출력한 개인 dashboard URL을 browser에서 연다. Baseline telemetry가 표시되는지 확인한 다음 Candidate B 배포와 traffic 실행 후 같은 dashboard에 새 `model_version`의 log, metric과 trace가 추가되는지 확인한다.

## 15. 생성물과 Git 정책

### 15-1. Git에서 관리할 것

- source code와 tests
- PhysioNet 공식 source archive, outcome, license와 checksum manifest
- DVC metadata와 params
- versioned YAML/TOML configuration과 schema
- GE expectation과 checkpoint
- Notebook source
- generic Compose, Kubernetes와 GitOps manifest
- Alloy config와 telemetry label 계약
- Grafana Cloud dashboard template, query와 Dashboard Importer app
- PhysioNet attribution/license와 canonical benchmark JSON evidence
- Feature decision summary와 canonical feature manifest
- README와 기획 문서

### 15-2. Git에서 제외할 것

- DVC cache와 generated snapshot/split
- GE runtime result와 generated Data Docs
- model binary와 metadata output
- MLflow DB와 run artifact
- JSONL event, metric과 trace output
- student assignment, IP, 실제 domain과 credential
- Grafana Cloud endpoint별 credential과 access token
- local `.env`, local secrets directory와 Kubernetes Secret의 실제 값
- Secret 값이 포함된 generated manifest와 shell history output
- 개인 설정으로 render된 dashboard JSON과 Grafana API response
- Notebook execution cache와 generated HTML
- full correlation, permutation importance, fold diagnostics와 transformed matrix

### 15-3. Prepared Evidence

수업에 필요한 고정 evidence를 Git에 포함해야 한다면 일반 runtime output과 분리한다.

```text
reference/
└── evidence/
    ├── data-quality/
    ├── feature-decisions/
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
| `apps/simple_mlops/alloy...` | `deploy/compose/simple-mlops`의 유일한 telemetry collector |
| data preparation wrapper | `apps/data-quality-pipeline` + `aiqa-data` |
| feature/target/label 상수 | `configs/contracts/model-input.yaml` + `aiqa-core` typed contract |
| model hyperparameter와 threshold 후보 | `configs/model/` |
| traffic 비율과 오류 주입 값 | `configs/traffic/scenarios.yaml` |
| release threshold와 rollback rule | `configs/qa/release-policy.yaml` |
| 공통 telemetry namespace와 logging policy | `configs/observability/telemetry.yaml` |
| Risk API metric 이름, label과 bucket | `configs/serving/api.yaml` |
| training과 MLflow 로직 | `aiqa-model` |
| prediction use case | `aiqa-serving` |
| process context, JSON log, metric registry와 trace | `aiqa-observability` platform SDK |
| release report와 approval rule | `aiqa-qa` |
| legacy의 외부 기술 구현 | 각 bounded context의 `adapters/` |
| root 파생 CSV | DVC managed output 경로 |
| app 내부 model/event 폴더 | root `artifacts/` |
| legacy Grafana dashboard/import code | 필요한 panel/query를 선별해 `deploy/grafana-cloud`와 `apps/grafana-dashboard-importer`로 재구현 |
| local Grafana/Loki/Tempo/Prometheus 배포 | 생성하지 않음 |

### 16-2. 현재 Package 보완

- `aiqa-data`에서 reference model 학습과 operational event 생성을 제거한다.
- 현재 `FEATURE_COLUMNS`, target, label과 default threshold 상수를 versioned config와 typed value object로 교체한다.
- YAML/JSON loader는 각 bounded context의 config adapter로 두고 domain/application에서 parser와 file path를 제거한다.
- `aiqa-model`을 model profile, evaluation, loading과 MLflow adapter로 세분화한다.
- `aiqa-observability`를 execution context, JSON logging, Prometheus registry와 OpenTelemetry module로 분리한다.
- `aiqa-observability`는 app metric semantics와 Grafana dashboard API를 갖지 않고 Alloy가 받을 표준 telemetry까지만 구현한다.
- Dashboard JSON 변환과 Grafana Cloud API 호출은 `apps/grafana-dashboard-importer`의 application/port/adapter로 격리한다.
- `tempo_trace_id`처럼 backend 이름이 포함된 API를 일반 trace/OTLP 용어로 교체한다.
- Grafana Cloud 환경 예시는 Alloy telemetry write 설정과 dashboard import 설정을 구분한다. Dashboard URL, 최소 권한 token, folder UID와 datasource UID는 유지하고 사용하지 않는 namespace 설정은 제거한다.
- `aiqa-serving`을 새로 만들고 HTTP와 독립된 prediction use case를 이동한다.
- `aiqa-qa`를 만들고 release evidence와 decision rule을 legacy 구현과 분리해 다시 정의한다.
- Legacy에서 선별해 가져오는 filesystem, MLflow, GE, FastAPI와 observability 연동 구현은 해당 package의 `adapters/` 아래에 재배치한다.
- Repository path에 의존하는 core helper를 app settings 또는 명시적 argument로 교체한다.
- Root workspace에는 다섯 app과 여섯 package만 member로 등록한다.
- Workspace lock은 root `uv.lock` 하나를 기준으로 한다.

## 17. 구현 단계

### 17-1. Phase 0: Data와 Model Feasibility

- PhysioNet source checksum과 4,000 patient/4,000 outcome join 확인
- 사망 554건, 생존 3,446건과 split/fold별 positive support 확인
- 최소 parser/aggregation spike로 patient-level feature table 생성
- Outcome-side descriptor와 identifier leakage 차단
- DummyClassifier와 단순 sklearn baseline repeated stratified cross-validation
- PR-AUC, AUROC, Precision, Recall, F1, confusion matrix와 불확실성 기록
- Train/valid 범위에서 Candidate A/B profile 가능성 탐색
- `F0`~`F2` feasibility report와 계속 진행/시나리오 수정 결정 기록
- Spike 코드는 production package로 간주하지 않고 Phase 2/4에서 TDD로 다시 구현
- Test와 release holdout은 이 단계에서 열지 않음

Phase 0 실행 결과는 `docs/reference/evidence/phase0/`에 보존한다. 현재 F0, F1과 F2는 모두 통과해 Phase 1 진행이 가능하다. 이 결론은 train/valid feasibility에 한정되며 Candidate B의 최종 `APPROVE`는 아니다. Phase 4에서 profile과 release policy를 freeze한 뒤 sealed test를 한 번 평가해야 canonical 교육 수치와 배포 여부가 확정된다.

### 17-2. Phase 1: 기준과 Workspace

- V2 branch 생성
- root workspace와 dependency group 정리
- target directory scaffold 생성
- `configs/` ownership, schema version과 config path 주입 규칙 확정
- App별 `BaseSettings` field, environment prefix, secrets directory와 source precedence contract 확정
- Structured config `BaseModel`과 runtime `BaseSettings`의 책임 분리 test 추가
- model input contract와 invalid configuration test를 먼저 작성
- bounded context와 public API 계약 정의
- `docs/adr/`와 첫 Architecture Decision Record 작성
- AS-IS 데이터, API, model artifact와 telemetry characterization test 추가
- import direction과 layer architecture test를 먼저 추가
- pytest marker와 root scenario test scaffold 추가
- baseline과 두 candidate 의사결정 test를 실패 상태로 먼저 작성
- generated path와 `.gitignore` 정책 적용

### 17-3. Phase 2: Data와 DVC

- PhysioNet Set A archive, outcome, license, citation과 source checksum 검증
- DVC 초기화, `params.yaml`, `dvc.yaml` 작성
- `physionet-record.yaml`, `aggregation.yaml`과 `quality-rules.yaml` schema 및 일관성 test 작성
- Patient record parser, `-1` sentinel normalization과 outcome join test 작성
- 48시간 aggregate와 patient-level deterministic stratified split unit test 작성
- Phase 0의 133개 available feature를 v1으로 재현하고 feature manifest, schema와 hash 생성
- Outcome/score leakage, split overlap, row count와 hash contract test 작성
- 실패 test를 기준으로 normalize/aggregate/split use case 구현
- Release holdout 기반 operational pool과 invalid request scenario test 구현
- DVC stage가 GE 실행과 독립적인지 검증

### 17-4. Phase 3: GE와 1일차 Lab

- Data Quality Pipeline app 생성
- EDA Notebook을 먼저 작성하고 수동 확인 항목을 고정
- expectation suite와 checkpoint 작성
- GE adapter contract test 작성
- Raw ingestion/processed readiness Validation Result와 Data Docs integration test
- 실제 missing sentinel, measurement coverage, outlier와 preprocessing 전후 evidence 검증
- GE가 V2 dataset publish를 차단하지 않고 evidence를 반환하는 contract test
- 1일차 Lab과 README 연결

### 17-5. Phase 4: Model과 MLflow

- Model Trainer app 생성
- model domain invariant와 evaluation use case test를 먼저 작성
- `feature-sets.yaml`, `profiles.yaml`과 `evaluation.yaml` loader 및 validation test 작성
- Train에서 dtype, 결측률, 분산, correlation, coefficient와 permutation importance 내부 diagnostics 생성
- Phase 0의 133개 전체 feature를 기본으로 제한된 feature set만 train/CV와 valid에서 비교
- Canonical `model-input.yaml`, feature 순서, dtype, preprocessing과 config hash를 test 전에 동결
- Train/valid와 cross-validation만 사용해 baseline, Candidate A와 Candidate B profile 탐색 및 확정
- feature selection, profile과 threshold가 train/valid만 사용하는지 leakage test 추가
- Aggregation, model input, release policy와 candidate profile을 freeze한 뒤 common test를 한 번 평가
- 실제 Precision, Recall, F1, AUROC, PR-AUC, threshold, support와 confusion matrix benchmark 생성
- Candidate A `HOLD`, Candidate B `APPROVE`가 실제 metric으로 재현되는지 확인
- Test 결과를 보고 policy threshold를 완화하거나 profile을 재선택하지 않는 audit test 추가
- 목표 관계가 test에서 성립하지 않으면 Candidate B를 승인하거나 배포하지 않고 scenario review 기록
- Canonical benchmark manifest와 재현 command 생성
- Exact value가 아닌 deterministic tolerance를 사용하는 scenario range test 통과
- MLflow dataset, run, model과 DVC provenance 연결
- Feature decision summary와 canonical feature manifest prepared evidence 생성
- MLflow adapter contract와 integration test 추가
- `aiqa-qa`의 최소 release policy와 decision use case를 TDD로 구현
- Target scenario를 채택한 경우 Candidate A `HOLD`와 Candidate B `APPROVE` scenario test 통과
- initial deployed baseline publish

V1 실행 상태는 `SCENARIO_REVIEW_REQUIRED`로 보존한다. 승인된 split revision V2에서는 `release-freeze.json`으로 train/valid 결과와 설정을 동결한 뒤 sealed test를 한 번 평가했으며 Candidate A `HOLD`, Candidate B `APPROVE`가 생성됐다. V2 canonical status는 `APPROVED`이고 `post_test_tuning_allowed=false`다. 따라서 V1 evidence를 덮거나 test에 맞춘 조정 없이 Phase 5~7 구현을 V2 기준으로 진행한다.

### 17-6. Phase 5: Serving과 Traffic

- Phase 4 canonical benchmark에서 Candidate B `APPROVE`가 실제로 확인되어야 진입
- V2 canonical evidence에서 Candidate B `APPROVE`를 확인하고 이 Phase를 진행
- `aiqa-serving` package 생성
- prediction use case와 port test를 먼저 작성
- Risk API module 분리와 FastAPI adapter integration test
- model reload와 response/event contract 검증
- Traffic Generator scenario behavior test와 네 scenario 구현
- `scenarios.yaml`에서 seed, traffic weight와 오류 주입 값을 읽도록 구현
- baseline serving, Candidate B smoke와 operational shift scenario test 통과
- API contract와 integration test 추가

### 17-7. Phase 6: Deployment와 Observability

- Compose stack 이동
- Kubernetes/Kustomize와 Argo CD asset 정리
- Python app별 read-only Secret volume, non-root file permission과 `secrets_dir` contract 적용
- `.env`가 container image와 GitOps asset에 포함되지 않는지 검증
- Risk API의 KServe HTTP adapter와 course model PVC publish adapter 구현
- service/model/trace label 계약 적용
- `telemetry.yaml`과 dashboard JSON label/query consistency test 추가
- Alloy config 정리와 Grafana Cloud 수신 smoke test
- 개인 stack용 dashboard template과 idempotent Dashboard Importer app을 TDD로 구현
- 고정 Dashboard UID/title, folder와 datasource binding unit test 추가
- Fake Grafana API adapter contract test와 선택적 live import smoke test 추가
- observability adapter contract test 추가
- Candidate B deploy와 baseline rollback 경로 smoke test
- Grafana, Loki, Tempo와 Prometheus server가 배포 대상에 없는지 manifest test

### 17-8. Phase 7: 교재와 End-to-End

- `aiqa-qa`의 quality issue, owner, next action과 reevaluation use case 완성
- Release Decision Lab adapter와 pytest scenario test 연결
- `ttamlops-2607`의 명령과 경로를 V2에 맞게 갱신
- Canonical benchmark manifest를 기준으로 교재의 model metric, threshold, confusion matrix와 dashboard 기준값 갱신
- 교재에 적힌 수치와 generated benchmark evidence가 일치하는지 docs consistency test 추가
- VS Code Remote-SSH와 제공 URL 기준으로 접속 문서 수정
- 수강생 dashboard import와 traffic 후 panel 확인 절차 작성
- localhost tunnel과 실제 domain hardcoding 제거
- 2일 14교시 흐름 검증
- 전체 scenario와 end-to-end test 실행
- 준비 상태 reset과 전체 smoke test 실행

## 18. 완료 기준

### 18-1. 기능 완료 기준

- DVC가 PhysioNet raw archive에서 patient-level split과 traffic pool을 재현하고 GE app이 raw/processed evidence를 생성한다.
- Phase 0의 133개 available feature가 versioned aggregation과 DVC revision으로 재현된다.
- Canonical model input은 train/CV와 valid만 사용해 test 전에 동결되고 결정 summary와 manifest가 남는다.
- Development와 operational 데이터 leakage가 없다.
- Baseline이 Dummy보다 유의미한 신호를 갖는지 feasibility evidence와 불확실성이 기록된다.
- Baseline, Candidate A와 Candidate B가 실제 model bundle과 MLflow run으로 생성된다.
- 세 model의 교육 수치가 canonical benchmark manifest에서 생성되고 `ttamlops-2607` 교재와 일치한다.
- Target scenario를 채택한 경우 Candidate A의 선택적 metric 개선과 guardrail 미충족이 재현되어 `HOLD`가 생성된다.
- Target scenario를 채택한 경우 Candidate B가 필수 release 기준을 충족해 `APPROVE`가 생성된다.
- Target scenario가 성립하지 않으면 test에 맞춘 policy/model 조작 없이 implementation gate를 중단하고 승인된 scenario 변경을 기록한다.
- Baseline model이 초기 상태에서 배포되어 있다.
- 같은 URL에서 Candidate B 배포를 확인하고 별도 smoke test로 baseline rollback 경로를 검증한다.
- Traffic scenario가 의도한 validation, distribution과 error 신호를 만든다.
- Log, metric과 trace를 service/model/request 기준으로 연결할 수 있다.
- Compose와 Kubernetes의 Alloy가 AIQA workload의 JSON log와 OTLP trace, Risk API의 bounded metric을 Grafana Cloud에 전달하며 local Grafana/Loki/Tempo/Prometheus server를 요구하지 않는다.
- 각 수강생이 자신의 Grafana Cloud stack에 고정 UID로 dashboard를 직접 생성하거나 갱신할 수 있다.
- Import한 dashboard에서 baseline telemetry와 Candidate B 배포 후 telemetry가 시간 순서로 누적된다.
- Feature contract, model profile, traffic scenario와 release policy가 versioned config에서 로드되고 config hash로 추적된다.
- Python app의 runtime 값은 app별 `BaseSettings`에서 검증되고 structured policy는 adapter의 `BaseModel`에서 별도로 검증된다.
- 배포 app은 필요한 Kubernetes Secret만 read-only volume으로 받아 `secrets_dir`에서 읽으며 실제 값은 Git과 image에 포함되지 않는다.
- Private OCI image는 kubelet 전용 `imagePullSecret`으로 pull하며 application process에는 해당 credential을 mount하지 않는다.
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
- Domain과 application layer에 feature 목록, release threshold, traffic 비율과 dashboard payload가 하드코딩되지 않는다.
- Package는 repository 상대 경로를 추측하지 않고 composition root에서 config path와 typed value를 주입받는다.

### 18-3. 검증 완료 기준

```text
uv lock / uv sync
Ruff
package unit tests
app unit tests
architecture dependency tests
configuration schema, cross-file consistency and hash tests
port/adapter contract tests
DVC repro and status
GE raw-ingestion/processed-readiness integration tests
baseline/two-candidate reproducibility tests
trainer/API integration tests
traffic scenario range tests
candidate decision and release scenario tests
Compose smoke test
Kubernetes manifest render and validation
Argo CD/KServe live 또는 inspection test
Alloy config validation과 Grafana Cloud ingestion smoke
dashboard JSON/query validation과 idempotent import test
personal dashboard baseline/Candidate B data accumulation smoke
README command replay
```

### 18-4. Engineering 완료 기준

- 새 use case는 실패하는 unit 또는 acceptance test에서 시작한다.
- Domain invariant는 framework 없이 unit test로 설명할 수 있다.
- Adapter는 자신이 구현하는 port의 contract test를 통과한다.
- Bounded context 간 dependency는 허용된 방향만 사용한다.
- Scenario test는 수강생 또는 QA 담당자가 이해할 수 있는 domain term으로 작성한다.
- Scenario test 안에서 release rule을 다시 구현하지 않고 application use case를 호출한다.
- Bug fix에는 같은 문제를 재현하는 regression test가 포함된다.
- Test fixture는 deterministic하며 clock, UUID와 random을 통제한다.
- Configuration 변경에는 parser/schema test와 영향받는 domain scenario test가 함께 포함된다.
- Refactor 후 architecture, unit, contract와 관련 scenario test를 모두 재실행한다.
- Coverage 수치는 보조 지표이며 behavior와 branch 누락 검토를 대체하지 않는다.

## 19. Version Control과 보류 사항

### 19-1. Branch와 Commit 원칙

V2 구현은 `main`에 직접 커밋하지 않는다. 현재 `feat/v2-monorepo` branch의 baseline commit `4bf4a8a`에서 시작하며 이후 변경은 다음 순서로 커밋한다.

```text
1. revised V2 planning document
2. PhysioNet source attribution and data/model feasibility evidence
3. characterization/architecture tests and workspace foundation
4. patient-level data/DVC/GE behavior and tests
5. actual model candidates, canonical benchmark and release decision tests
6. serving, deployment, Alloy observability and scenario tests
7. benchmark-backed labs/docs and end-to-end verification
```

Implementation과 해당 test는 같은 변경 단위로 commit한다. 구조 변경만 하고 test를 나중 commit으로 미루지 않는다.

### 19-2. 구현 전 확정할 항목

- 수강생 개인 Grafana Cloud 가입을 사전 준비로 할지 수업 중 진행할지 여부
- 개인 stack의 최소 dashboard write 권한과 token 발급 절차
- 개인 dashboard에서 사용할 logs/metrics/traces datasource UID 확인 방식
- API와 MLflow 개인 URL의 인증 및 권한 방식
- Argo CD Application 이름과 학생 RBAC 규칙
- `apps.learn` 계열 canonical domain 확정
- KServe live 실습 범위와 fallback 조건
- Prepared evidence를 Git에 포함할 최소 범위
- Course 시작 상태 reset과 검증 command
- Architecture test를 AST로 유지할지 전용 import boundary 도구를 도입할지
- Domain/application test coverage의 최소 guardrail

Baseline/Candidate A/Candidate B의 algorithm, threshold와 metric 허용 범위는 계획 단계에서 꾸며낼 값이 아니라 Phase 0 feasibility와 Phase 4 canonical benchmark의 산출물이다. GE publish gate는 V2에서 사용하지 않는 것으로 확정했다.
