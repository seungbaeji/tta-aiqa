# TTA AI 서비스 품질 실습 저장소

PhysioNet 2012 데이터에서 시작해 모델 평가, API 서빙, 운영 관측과 배포 판단까지
이어지는 V2 실습 공간입니다. 이 저장소는 수강생 실습 코드와 Lab 실행 자산만
둡니다. 교재와 126장 슬라이드 원고는 비공개 교육자료 저장소에서 관리합니다.
수강생 본편의 첫 사건은 데이터 EDA가 아니라
[배포된 baseline 관찰](labs/README.md#배포된-baseline-관찰)입니다. 대상
baseline이 아직 없으면 그 사실을 숨기지 않고 OFFLINE 또는 `target_pending`으로
적습니다. 수강생은 [실습 안내](labs/README.md)에서 시작합니다.
이전 강의와 Simple MLOps 구현은 `tmp/legacy/`에 보존하며 실행 의존이 아닙니다.

## 먼저 갈 곳

- 수강생: [실습 안내의 아홉 단계](labs/README.md)
- 강사: [환경 준비](#2-준비)와 `uv run python scripts/setup_course.py`
- 개발자: [저장소 구조](#1-구조)와 [구현 검증](#8-구현-검증)

## 1. 구조

### 1-1. 현재 작업 대상

```text
apps/       여섯 개 실행 프로그램과 조립 지점
packages/   다섯 업무 영역과 공통 관측 도구
data/       PhysioNet 공식 원본과 생성 데이터 경계
artifacts/  모델, 품질 결과와 MLflow 로컬 상태
configs/    버전이 지정된 데이터·모델·서빙·QA·관측 규약
docs/       Lab이 여는 공식 evidence JSON
scripts/    강사 준비와 재현 명령
tests/      구조, 설정, 시나리오와 통합 검증
tmp/        Git이 추적하지 않는 다운로드와 보관 공간
```

### 1-2. 패키지 역할

```text
packages/aiqa-core/            공통 모델 입력 특성 규약
packages/aiqa-data/            PhysioNet 정규화, 집계, 분할과 계보
packages/aiqa-model/           특성 준비, 학습, 평가와 MLflow
packages/aiqa-serving/         프레임워크와 분리된 예측 흐름
packages/aiqa-observability/   Python 프로그램의 로그, trace와 지표 도구
packages/aiqa-qa/              배포 근거와 판단
```

업무 패키지는 `domain -> application/ports -> adapters` 의존 방향을 지키며,
각 실행 프로그램이 필요한 구현을 조립합니다. `aiqa-observability`는 특정 업무
영역에 속하지 않는 공통 도구입니다. 구조 검사가 패키지 사이의 잘못된 직접 의존과
`legacy` 가져오기를 차단합니다.

## 2. 준비

### 2-1. 실행 위치

강사가 제공한 Linux VM에 VS Code Remote SSH로 접속한 터미널을 기본 실행 환경으로
사용합니다. 접속 입력은 강사가 알려 준 **SSH alias 하나**입니다. HostName,
비밀번호, ProxyJump는 이 저장소에 없습니다. bastion 경로는 현재 P0 pending이며
`tmp/legacy/`를 실행 설정으로 복사하지 않습니다.

개인 PC에서는 `setup_course.py --data-only`로 데이터와 노트북의 정적
실습만 준비할 수 있습니다. 개인 PC의 결과를 Docker, `kubectl`, Grafana Cloud나
대상 환경의 실행 근거로 쓰지 않습니다.

수업에서 직접 여는 주소는 두 종류입니다. 둘을 섞어 보고하지 않습니다.

- 로컬 Compose Risk API: `http://127.0.0.1:8000`
- 대상 Risk API: 강사가 준 URL. 노트북 변수는 `AIQA_RISK_API_URL`

대상 URL이 없으면 대상 LIVE를 하지 않고
[실습 안내 API 계약](labs/README.md#api-접근-계약)의 OFFLINE을 따릅니다.
수강생은 ClusterIP에 붙이려고 port-forward나 tunnel을 만들지 않습니다.
VS Code Remote SSH의 로컬 포트 전달은 VM 안 `127.0.0.1` 서비스용입니다.

4장 Grafana는 강사가 LIVE 대시보드 URL을 주거나, 준비된 오프라인 수집 묶음을
쓰게 합니다. MLflow 화면은 VM Compose를 VS Code 포트 전달로 열거나 강사가 준
주소를 사용합니다. 4GiB 메모리 한도는
[실습 안내](labs/README.md#4gib-vm-메모리)를 따릅니다.

### 2-2. uv 설치

`uv`가 없다면 과정에서 확인한 버전의 설치 스크립트를 파일로 내려받아
내용을 확인한 뒤 실행합니다. 현재 과정 고정 버전은 `0.11.12`입니다.

```bash
curl -LsSf https://astral.sh/uv/0.11.12/install.sh \
  -o /tmp/uv-0.11.12-install.sh
less /tmp/uv-0.11.12-install.sh
sh /tmp/uv-0.11.12-install.sh
uv --version
```

Windows PowerShell에서는 다음 명령을 사용합니다.

```powershell
$installer = Join-Path $env:TEMP "uv-0.11.12-install.ps1"
irm https://astral.sh/uv/0.11.12/install.ps1 -OutFile $installer
Get-Content $installer
powershell -ExecutionPolicy ByPass -File $installer
uv --version
```

관리형 강의 VM에서는 강사가 미리 설치한 바이너리를 사용합니다. 다운로드와
추가 설치 옵션은 uv 공식 문서의 설치 페이지에서 확인합니다.

```text
https://docs.astral.sh/uv/getting-started/installation/
```

### 2-3. 의존성 설치

의존성을 설치합니다.

```bash
uv sync --all-packages --group dev --group notebook
```

### 2-4. 실습 환경 준비

제공된 VM에서는 공식 데이터를 재현하고 GE 검증을 실행한 뒤 기준 모델의 준비
상태를 확인합니다. 이 명령은 Git에서 제외된 로컬 데이터와 실행 결과만 만들며
`docs/reference/evidence/`의 V2 공식 기록은 수정하지 않습니다.

```bash
uv run python scripts/setup_course.py
```

기준 모델이 준비되지 않은 일반 복제본에서 데이터 실습만 준비하려면
`--data-only`를 사용합니다.

```bash
uv run python scripts/setup_course.py --data-only
```

## 3. 데이터 준비

### 3-1. 공식 원본

PhysioNet Challenge 2012 Set A의 ODC-By 1.0 고지와 체크섬 목록은
`data/raw/physionet-2012/`에서 관리합니다. 준비 명령은 공식 압축 파일과 결과
파일을 내려받아 체크섬을 검증합니다. 원본과 생성 데이터는 Git이 아니라 로컬 DVC
흐름으로 관리합니다.

### 3-2. DVC 재현

저장소 루트에서 다음 명령을 실행합니다.

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

4,000개 개별 기록을 사용할 수 있는 특성 133개로 집계하고 고정된 난수로
`train 2,400 / valid 600 / test 600 / operational 400`으로 나눕니다.
`operational.csv`에는 정답인 `target` 열을 넣지 않습니다.

승인된 V2 분할은 V1의 공식 평가 자료를 재사용하지 않고 역할을 다시 고정합니다.

```text
data/splits/physionet-2012/revisions/v2/datasets/
  train.csv        2,900건
  valid.csv          600건
  test.csv           400건, 한 번만 여는 공식 평가 전용
  operational.csv    100건, target 미포함
```

현재 `dvc.lock`은 데이터 처리 흐름의 재현 기준입니다. V2 배포 판단에서 사용한
과거 데이터 계보는 `docs/reference/evidence/data-lineage/revisions/v2/`에 읽기
전용으로 보존합니다. 수강생은 이 근거를 읽되 현재 데이터 재현 결과로 덮어쓰지
않습니다.

## 4. 데이터 품질 실습

### 4-1. 수동 EDA

VS Code에서 `labs/ch01-data-quality/01_physionet_data_quality_eda.ipynb`를 열고
위에서 아래로 실행합니다. 원본 측정 범위, `-1` 결측 표식, 48시간 범위, 정답
연결과 가공 뒤 결측률을 확인합니다.

### 4-2. Great Expectations

EDA에서 확인한 규칙을 자동 검증으로 실행합니다.

```bash
uv run python scripts/validate_data.py
```

실행 검증 결과와 Data Docs는
`artifacts/data-quality/great-expectations/`에 생성됩니다. GE 결과는 데이터
품질 근거이며 DVC 데이터 게시를 자동으로 막는 조건은 아닙니다.

수강생 전체 동선은 [labs/README.md](labs/README.md)에서 시작합니다.

## 5. 모델 품질

### 5-1. 현재 공식 결과

모델 프로필, 임계값과 배포 정책을 학습·교차검증 자료와 검증 자료에서 고정한 뒤
공식 평가 자료를 한 번만 열었습니다.

```bash
uv run python scripts/run_model.py status --revision v2
```

V1 evidence는 `HOLD/HOLD`로 보존되어 있습니다. 승인된 V2 revision은 Candidate A `HOLD`, Candidate B `APPROVE`이며 Candidate B 배포가 허용됩니다.

V2 공식 평가의 핵심 결과는 다음과 같습니다.

| Profile | Threshold | PR-AUC | Precision | Recall | FN | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline | 0.50 | 0.5244 | 0.5652 | 0.2364 | 42 | Reference |
| Candidate A | 0.40 | 0.5942 | 0.7727 | 0.3091 | 38 | HOLD |
| Candidate B | 0.35 | 0.5743 | 0.3793 | 0.8000 | 11 | APPROVE |

### 5-2. One-shot 규칙

`docs/reference/evidence/model/revisions/v2/canonical-benchmark.json`에
`evaluated_once`가 기록되어 있으므로 공식 평가는 다시 실행할 수 없습니다. 결과에
맞춰 특성, 임계값, 모델 프로필이나 배포 정책을 바꾸지 않습니다. 변경이 필요하면
기존 근거를 덮지 않는 새 개정본을 만듭니다.

### 5-3. MLflow 확인

강사용 환경 준비에서는 세 모델 묶음과 MLflow 실행을 만들고 기준 모델만 초기 배포
경로에 게시합니다. 수강생 VM에는 이 상태가 미리 준비됩니다. V2는 공식 평가가
끝난 과거 개정본이므로 모델 학습 흐름을 다시 실행하지 않습니다.

```bash
uv run python scripts/run_model.py status --revision v2
```

V2의 모델 준비 결과와 실행 ID는
`docs/reference/evidence/model/revisions/v2/model-bootstrap.json`에서 확인합니다.
새 개정본에서는 개발 평가와 진단을 마치고 `release-freeze.json`을 커밋한 뒤에만
공식 평가를 열 수 있습니다. 모델 게시와 기준 모델 복구는 수강생 활동이 아닙니다.
강사 또는 플랫폼 담당자는 `scripts/publish_model.py`와 승인된 배포 절차를
사용하고, 수강생은 준비된 `deployment.json`과 모델 근거를 읽습니다.

Compose의 MLflow service만 시작합니다. 3장에서 같은 Compose stack을 확장하므로
별도 `mlflow server`를 실행하지 않아 포트 `5000`이 충돌하지 않습니다.
게시 포트는 기본적으로 `127.0.0.1`에만 연결됩니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d mlflow
curl http://127.0.0.1:5000/health
```

VS Code 포트 전달 또는 강사가 제공한 주소로 MLflow 화면을 엽니다. 실행 기록에는
평가와 데이터 역할, DVC 잠금 파일, 모델·데이터 설정의 SHA-256이 남습니다.

Candidate B 게시 명령은 `release-manifest.json`의 평가 뒤 승인과 모델·메타데이터
해시를 모두 검증합니다. V2 과거 근거의 대조 범위는
`docs/reference/evidence/model/revisions/v2/README.md`에서 확인합니다.

## 6. Serving과 Traffic

### 6-1. Compose 실행

Compose에서는 Risk API가 로컬 scikit-learn 어댑터를 사용합니다.
MLflow와 Risk API, Alloy 관리 포트는 기본적으로 로컬 호스트에만 게시됩니다.
통제된 원격 실습 환경에서 외부 인터페이스가 꼭 필요할 때만
`AIQA_COMPOSE_BIND_HOST`를 명시합니다. 예를 들어
`AIQA_COMPOSE_BIND_HOST=0.0.0.0`은 인증되지 않은 실습 서비스를 네트워크에
노출하므로 방화벽과 접근 제어가 준비된 환경에서만 사용합니다.

수강생 실행 명령의 단일 원본은
[`labs/ch03-serving/README.md`](labs/ch03-serving/README.md)입니다. 강사는
강의 시작 전에 이미지를 미리 빌드합니다.

API contract probe는 [3장 서빙 README](labs/ch03-serving/README.md)의
Risk API 기동·health/model 확인과 `01_verify_risk_api.ipynb` 실행을 따릅니다.
이 probe는 정상 200과 의도한 422를 한정 확인하며 P5 collection manifest를 만들지
않습니다. P5 세 시나리오는 [4장 운영 관측](labs/ch04-observability/README.md)에서
관측 조건을 먼저 고정한 뒤 실행합니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --no-build risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
uv run jupyter nbconvert --to notebook --execute \
  labs/ch03-serving/01_verify_risk_api.ipynb \
  --output /tmp/ch03-risk-api.ipynb \
  --ExecutePreprocessor.timeout=120
```

4장에서 Grafana `rate()`를 비교할 때는 Alloy override를 함께 사용하고
`--fast` 없이 수집 간격을 따릅니다.

### 6-2. 관측 환경

Grafana 접속 정보, Alloy 설정, 대시보드 가져오기와 이미지 빌드는 강사 또는 환경
담당자가 강의 시작 전에 준비합니다. 수강생은
[`labs/ch04-observability/README.md`](labs/ch04-observability/README.md)에서
LIVE와 PREPARED/OFFLINE 가운데 하나를 고르고 선택한 경로의 품질 근거만
확인합니다. 운영자용 Alloy 설정은
[`deploy/compose/simple-mlops/secrets/alloy/README.md`](deploy/compose/simple-mlops/secrets/alloy/README.md)에 있습니다.

### 6-3. Trace 경계

요청 생성기를 한 번 실행하면 `traffic.generate` 최상위 span이 생기고, 각 예측
요청은 다음과 같이 연결됩니다.

```text
traffic.generate
  -> risk-api.predict (CLIENT)
      -> POST /v1/predict (SERVER)
          -> risk.predict
```

Kubernetes에서 KServe backend를 선택하면 `risk.predict` 아래에 Risk API의
`kserve.infer` CLIENT span, KServe HTTP SERVER span, KServe 쪽
`kserve.infer` operation이 이어집니다. Traffic Generator는 CLIENT span 안에서
W3C `traceparent`, `X-Request-ID`, `X-AIQA-Run-ID`, `X-AIQA-Scenario`를 Risk
API로 전달합니다. Risk API의 KServe CLIENT span은 trace context와 request ID를
KServe로 전달합니다.

- `/health/*`, `/metrics`, KServe readiness는 반복 probe이므로 trace에서 의도적으로 제외합니다.
- 요청과 예측 지표는 허용된 시나리오를 공통 레이블로 사용합니다. 요청 ID, 실행
  ID와 trace ID는 JSONL, 구조화 로그와 Tempo trace를 연결하는 데만 쓰며
  Prometheus 지표 레이블이나 집계 기준으로 사용하지 않습니다.

## 7. Kubernetes 배포

### 7-1. 선언 파일 확인

Kubernetes에서는 외부 Risk API가 내부 KServe V2 예측기를 호출합니다.
`kserve.infer` CLIENT span이 W3C 추적 정보와 요청 ID를 전달합니다. 기본 설정은
기준 모델로 시작하고 Candidate B와 되돌리기는 별도 overlay로 둡니다.
각 overlay는 PVC 하위 경로와 `model-identity` ConfigMap의 예상 모델 SHA-256을
함께 고릅니다. 수강생은 로컬 렌더링과 계약 검사로 선언 파일을 읽고, 서버 측
검사·모델 게시·Secret·실제 동기화는 플랫폼 담당자가 수행합니다.

Private GHCR image와 `ghcr-pull` Secret의 준비 방식은
[`deploy/kubernetes/README.md`](deploy/kubernetes/README.md)에 분리해 두었습니다.

## 8. 구현 검증

### 8-1. 정적 검증과 테스트

강의 시작 전 점검은 `uv run python scripts/course_preflight.py`로 수행합니다.
결과는 `artifacts/reports/course-preflight.json`에 남깁니다. 과정 설계와
강사 runbook은 비공개 교육자료 저장소에서 관리합니다.

```bash
uv lock --check
uv run ruff check apps packages scripts tests
uv run pytest -q
uv run dvc status
```

### 8-2. 테스트 경계

핵심 로직은 단위 검사에서 확인하고 파일, YAML, scikit-learn, MLflow, FastAPI,
노트북과 배포 규약은 통합 검사에서 확인합니다.

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

이전 Simple MLOps app과 package는 `tmp/legacy/apps/`와 `tmp/legacy/packages/`에 보존합니다. 새 V2 코드는 `legacy`를 import하지 않으며 architecture test가 이를 검증합니다.

## 10. 과정 설계

과정 설계, ADR, 강사 runbook과 Lab이 열지 않는 과거 근거는 비공개 교육자료
저장소에서 관리합니다. 이 저장소의 `docs/reference/evidence/`에는 수강생 Lab이
여는 V2 JSON만 둡니다.
