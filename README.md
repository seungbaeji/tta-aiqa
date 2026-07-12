# TTA AIQA Monorepo

PhysioNet 2012 기반의 데이터, 모델, serving과 운영 품질 교육을 하나의 실행 흐름으로 구성하는 V2 작업 공간입니다. 이전 course/lab과 Simple MLOps 구현은 `legacy/` 아래에 보존합니다.

## 1. 구조

### 1-1. 현재 작업 대상

```text
apps/       여섯 개 독립 실행 process와 composition root
packages/   다섯 bounded-context와 하나의 platform SDK
data/       PhysioNet 공식 원본과 생성 데이터 경계
configs/    versioned data/model/serving/QA/telemetry 계약
docs/       V2 기획과 Architecture Decision Record
scripts/    강사 준비와 재현 command
tests/      architecture/configuration/scenario/integration/e2e 검증
legacy/     AS-IS apps, labs, packages, artifacts와 docs 보관
```

### 1-2. Package 역할

```text
packages/aiqa-core/            공유 canonical feature contract
packages/aiqa-data/            PhysioNet 정규화, 집계, split과 lineage
packages/aiqa-model/           feature preparation, 학습, 평가와 MLflow
packages/aiqa-serving/         framework 독립 prediction use case와 port
packages/aiqa-observability/   모든 Python app의 context, JSON log, trace와 metric SDK
packages/aiqa-qa/              release evidence와 decision
```

비즈니스 package는 `domain -> application/ports -> adapters` 의존 방향을 지키고 app이 composition root에서 조립합니다. `aiqa-observability`는 business bounded context가 아닌 platform SDK로서 AIQA package를 import하지 않습니다. Architecture test가 package 간 직접 의존과 `legacy` import를 차단합니다.

## 2. 준비

### 2-1. 실행 위치

모든 실습 명령은 강사가 제공한 Linux VM의 VS Code Remote SSH terminal에서
실행합니다. 수강생의 Windows, macOS 또는 Linux PC는 VS Code와 browser를 위한
host일 뿐이며, repository, Docker, kubectl과 data는 VM에서만 사용합니다.

수업에서 수강생이 확인하는 user-facing URL은 두 개입니다.

- 강사가 제공하는 Risk API URL
- 4장에서 각자 생성하는 Grafana Cloud dashboard URL

MLflow UI는 VM의 Compose service를 VS Code port forwarding으로 열거나 강사가
제공한 URL을 사용합니다.

### 2-2. uv 설치

`uv`가 없다면 먼저 설치합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell에서는 다음 명령을 사용합니다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

다운로드와 추가 설치 옵션은 uv 공식 문서의 설치 페이지에서 확인합니다.

```text
https://docs.astral.sh/uv/getting-started/installation/
```

### 2-3. 의존성 설치

의존성을 설치합니다.

```bash
uv sync --all-packages --group notebook
```

### 2-4. 실습 환경 준비

제공 VM에서는 공식 데이터를 재현하고 GE validation을 실행한 뒤 baseline
model 준비 상태를 확인합니다. 이 명령은 local data와 ignored runtime artifact만
생성하며 `reference/evidence/`의 historical V2 기록을 수정하지 않습니다.

```bash
uv run python scripts/setup_course.py
```

Baseline model이 사전 배포되지 않은 일반 clone에서 데이터 실습만 준비하려면 `--data-only`를 사용합니다.

```bash
uv run python scripts/setup_course.py --data-only
```

## 3. 데이터 준비

### 3-1. 공식 원본

PhysioNet Challenge 2012 Set A의 ODC-By 1.0 고지와 checksum manifest는 `data/raw/physionet-2012/`에서 관리합니다. 준비 명령이 공식 archive와 outcome을 내려받아 checksum을 검증하며, 원본 파일과 생성 데이터는 Git이 아니라 local DVC pipeline이 관리합니다.

### 3-2. DVC 재현

Repository root에서 다음 명령을 실행합니다. Python wrapper이므로 Windows, macOS와 Linux에서 동일합니다.

```bash
uv run python scripts/prepare_data.py
```

생성 결과:

```text
data/interim/physionet-2012/set-a/
data/processed/physionet-2012/patient-features.csv
data/splits/physionet-2012/split-manifest.csv
data/splits/physionet-2012/datasets/{train,valid,test,operational}.csv
```

4,000개 patient record를 133개 available feature로 집계하고 고정 seed로 `train 2,400 / valid 600 / test 600 / operational 400`으로 분할합니다. `operational.csv`에는 정답인 `target` 열을 포함하지 않습니다.

승인된 V2 split revision은 V1의 sealed test를 재사용하지 않고 역할을 다시 고정합니다.

```text
data/splits/physionet-2012/revisions/v2/datasets/
  train.csv        2,900건
  valid.csv          600건
  test.csv           400건, sealed one-shot 평가 전용
  operational.csv    100건, target 미포함
```

현재 `dvc.lock`은 active data-pipeline 구현의 재현 기준입니다. sealed V2
release가 참고한 historical data lineage는
`reference/evidence/data-lineage/revisions/v2/`에 read-only로 보존합니다.
수강생은 V2 evidence를 읽되, 이를 현재 data 재현 결과로 덮어쓰지 않습니다.

## 4. 데이터 품질 실습

### 4-1. 수동 EDA

VS Code에서 `labs/ch01-data-quality/01_physionet_data_quality_eda.ipynb`를 열고 위에서 아래로 실행합니다. Raw measurement coverage, `-1` sentinel, 48시간 범위, outcome join과 processed missingness를 확인합니다.

### 4-2. Great Expectations

EDA에서 확인한 규칙을 자동 검증으로 실행합니다.

```bash
uv run python scripts/validate_data.py
```

Runtime Validation Result와 Data Docs는 `artifacts/data-quality/great-expectations/`에 생성됩니다. GE 결과는 품질 evidence이며 DVC dataset publish를 차단하는 gate가 아닙니다.

수강생 전체 동선은 [labs/README.md](labs/README.md)에서 시작합니다.

## 5. 모델 품질

### 5-1. 현재 canonical 결과

모델 profile, threshold와 release policy를 train/CV와 valid에서 동결한 뒤 sealed test를 한 번 평가했습니다.

```bash
uv run python scripts/run_model.py status --revision v2
```

V1 evidence는 `HOLD/HOLD`로 보존되어 있습니다. 승인된 V2 revision은 Candidate A `HOLD`, Candidate B `APPROVE`이며 Candidate B 배포가 허용됩니다.

V2 sealed test의 핵심 결과는 다음과 같습니다.

| Profile | Threshold | PR-AUC | Precision | Recall | FN | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 0.50 | 0.5244 | 0.5652 | 0.2364 | 42 | Reference |
| Candidate A | 0.40 | 0.5942 | 0.7727 | 0.3091 | 38 | HOLD |
| Candidate B | 0.35 | 0.5743 | 0.3793 | 0.8000 | 11 | APPROVE |

### 5-2. One-shot 규칙

`reference/evidence/model/revisions/v2/canonical-benchmark.json`에 `evaluated_once`가 기록되어 있으므로 sealed test 재실행은 차단됩니다. Test 결과에 맞춰 feature, threshold, model profile이나 release policy를 변경하지 않습니다. 변경이 필요하면 기존 evidence를 덮지 않는 새 revision을 만듭니다.

### 5-3. MLflow 확인

강사용 환경 준비에서는 세 model bundle과 MLflow run을 생성하고 baseline만 초기 deployed 경로에 publish합니다. 수강생 VM에는 이 상태가 미리 준비됩니다. V2는 이미 sealed test가 확정된 historical revision이므로 Model Trainer lifecycle을 다시 실행하지 않습니다.

```bash
uv run python scripts/run_model.py status --revision v2
```

V2의 기존 bootstrap 결과와 run ID는 `reference/evidence/model/revisions/v2/model-bootstrap.json`에서 확인합니다. 새 revision에서는 development, diagnostics, bootstrap으로 train/valid 결과를 만들고 `release-freeze.json`을 commit한 뒤에만 final을 열 수 있습니다. 승인된 Candidate B를 local deployed 경로로 전환하거나 baseline으로 되돌릴 때는 다음 명령을 사용합니다.

```bash
uv run python scripts/publish_model.py candidate-b --revision v2
uv run python scripts/publish_model.py baseline --revision v2
```

Compose의 MLflow service만 시작합니다. 3장에서 같은 Compose stack을 확장하므로
별도 `mlflow server` process를 띄우지 않아 port `5000`이 충돌하지 않습니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d mlflow
curl http://127.0.0.1:5000/health
```

VS Code port forwarding 또는 강사가 제공한 MLflow URL로 UI를 엽니다. Run에는
evaluation role, 접근한 dataset role, DVC lock과 model/data configuration
SHA-256이 기록됩니다.

Candidate B publish는 `release-manifest.json`의 post-test approval과 model/metadata
digest를 모두 검증합니다. V2의 historical reconciliation scope는
`reference/evidence/model/revisions/v2/README.md`에서 확인합니다.

## 6. Serving과 Traffic

### 6-1. Compose 실행

Compose에서는 Risk API가 local sklearn adapter를 사용합니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --build
curl http://127.0.0.1:8000/health/ready
```

독립 Traffic Generator로 baseline 요청을 보냅니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
```

### 6-2. Grafana Cloud 연결

`deploy/compose/simple-mlops/secrets/alloy/README.md`에 적힌 일곱 개 개인 설정 파일을 만든 후 Alloy override를 함께 실행합니다. Repository는 Grafana, Loki, Tempo 또는 Prometheus server를 배포하지 않습니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d --build
```

Dashboard Importer용 값은 개인 `.env.grafanacloud` 또는 `/var/run/secrets/aiqa/grafana-dashboard-importer`에 별도로 둡니다. Alloy write token과 dashboard token은 공유하지 않습니다.

```bash
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

고정 UID `tta-aiqa-quality`가 생성되거나 갱신되며 실행 결과에 개인 dashboard URL이 출력됩니다.

Alloy override에서는 Risk API의 Prometheus metric과 Compose workload의 JSON log/OTLP trace를 전송합니다. traffic profile을 실행하면 같은 trace policy로 생성된 traffic process log와 trace도 개인 stack에 누적됩니다.

## 7. Kubernetes 배포

### 7-1. Immutable model publish

강사 환경에서 course model PVC가 `/mnt/course-models`에 연결되어 있다고 가정하면 승인된 bundle을 hash 경로에 publish합니다. 같은 hash는 idempotent하며 기존 경로를 덮어쓰지 않습니다.

```bash
uv run python scripts/publish_model.py candidate-b \
  --revision v2 \
  --target-root /mnt/course-models
```

### 7-2. Manifest 확인

Kubernetes에서는 외부 Risk API가 내부 KServe V2 custom predictor를 호출합니다. Base는 baseline으로 시작하고 Candidate B와 rollback은 별도 overlay입니다. `/mnt/course-models`는 단일 노드 수업 VM의 static model PV에 연결됩니다. 각 overlay는 PVC subPath와 non-secret `model-identity` ConfigMap의 expected model SHA-256을 함께 선택하며 predictor는 mount된 bundle이 다르면 시작을 거부합니다. Private GHCR image pull용 `ghcr-pull` Secret은 강사가 사전에 provision하며 Grafana Cloud Secret과 별개입니다. Alloy는 개인 Grafana Cloud Secret을 준비한 뒤 observed overlay에서만 추가합니다.

```bash
kubectl kustomize deploy/kubernetes/overlays/baseline >/tmp/tta-aiqa-baseline.yaml
kubectl kustomize deploy/kubernetes/overlays/candidate-b >/tmp/tta-aiqa-candidate-b.yaml
kubectl kustomize deploy/kubernetes/overlays/rollback >/tmp/tta-aiqa-rollback.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-baseline.yaml
```

실제 sync는 강사가 제공한 Argo CD 절차를 따릅니다. `alloy-grafana-cloud` Secret에는 각 수강생의 개인 Grafana Cloud write 설정만 저장하며, Secret 준비 전에는 Alloy component를 포함하지 않습니다.

Private GHCR image와 `ghcr-pull` Secret의 준비 방식은
[`deploy/kubernetes/README.md`](deploy/kubernetes/README.md)에 분리해 두었습니다.

## 8. 구현 검증

### 8-1. 정적 검증과 테스트

```bash
uv lock --check
uv run ruff check apps packages scripts tests
uv run pytest -q
uv run dvc status
```

실제로 완료한 local 검증과 target k3s/Grafana Cloud에서 남은 검증은 [V2 구현 검증 상태](docs/v2-implementation-verification.md)에 구분해 기록합니다.

### 8-2. 테스트 경계

핵심 로직은 unit suite에서 실행하고, 파일·YAML·sklearn·MLflow·FastAPI·Notebook·배포 계약은 integration suite에서 실행합니다.

```bash
uv run pytest -q tests/unit
uv run pytest -q tests/integration
```

전체 검증은 두 suite를 합쳐 실행합니다.

```bash
uv run pytest -q
```

## 9. Legacy

### 9-1. 이전 자료 위치

이전 Simple MLOps app과 package는 `legacy/apps/`와 `legacy/packages/`에 보존합니다. 새 V2 코드는 `legacy`를 import하지 않으며 architecture test가 이를 검증합니다.

## 10. 기획 문서

### 10-1. V2 TO-BE 계획

기존 2일 14교시 구성, repository 경계, 데이터·모델 계보, conditional deployment gate, Grafana Cloud와 수강생 동선은 [docs/v2-to-be-plan.md](docs/v2-to-be-plan.md)에 정리했습니다.

### 10-2. Artifact Identity ADR

Git, DVC, MLflow, immutable model/image artifact와 release manifest의 역할 분리는 [ADR 0006](docs/adr/0006-layered-artifact-identity-and-release-provenance.md)에 기록합니다. 이 문서는 어떤 hash를 왜 쓰는지와 SLSA, KServe, Grafana Alloy, Great Expectations, k6를 교육 범위에서 어떻게 참조하는지 설명합니다.
