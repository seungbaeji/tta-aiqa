# 실습 안내

이 과정은 이미 배포된 baseline에서 출발해 데이터, 모델, API, 배포, 관측과
rollback 권고까지 하나의 품질 판단 사건을 닫습니다. `target_pending`은 대상
운영 환경을 아직 확인하지 못한 운영 scope입니다. `static`과 `offline`은 정적/미실행
evidence scope이고, 실제 실행 범위는 `local` 또는 `target`으로 기록합니다. 실행이
막힌 경우에는 scope와 별도로 `result=BLOCKED`와 사유, 담당자를 남깁니다.

큰 단계는 H2, 한 번에 내려야 할 판단은 H3입니다. 다섯 장 폴더는 자료와 실행
경계를 보존하고, 아래 9단계가 그 사이의 학습 순서를 소유합니다.

**시작 전 확인**

강사가 알려 준 SSH alias 하나로 제공된 VM에 접속합니다. HostName, 비밀번호,
ProxyJump와 P0 네트워크 복구를 이 저장소에서 추측하지 않습니다. 개인 PC에서는
`--data-only` 정적 경로만 사용합니다. 개인 PC의 정적 결과를 Docker, Kubernetes나
대상 환경의 실행 근거로 쓰지 않으며, Grafana의 LIVE 관측 결과로 바꾸지도 않습니다.

KServe 설치, GHCR credential, Argo Application 생성/sync, WireGuard 복구는
강사와 플랫폼 범위입니다.

```bash
uv sync --all-packages --group dev --group notebook
uv run python scripts/setup_course.py
```

개인 PC에서 데이터와 노트북의 정적 경로만 준비할 때는 다음 명령을 사용합니다.

```bash
uv sync --all-packages --group dev --group notebook
uv run python scripts/setup_course.py --data-only
```

대상 URL이 없으면 대상 LIVE를 시도하지 않습니다. 수업용 대상 주소는 가상
컴퓨터 이름에서 만든 공개 HTTPS입니다. `ttaN-pve2-lab`은
`https://ttaN-pve2.apps.learn.mrml.dev`, `ttaN-pve3-lab`은
`https://ttaN-pve3.apps.learn.mrml.dev`입니다. Proxmox 로그인
`https://pve2.homelab.mrml.dev/`와 `https://pve3.homelab.mrml.dev/`는 Risk API가
아닙니다. 로컬 Compose는 `http://127.0.0.1:8000`이며 가상 컴퓨터 안에서만
씁니다. 화면 IPv4의 80번은 수업 대상이 아닙니다. 대상 URL을 명령에 넣을 때는
`AIQA_RISK_API_URL`로만 전달합니다. ClusterIP, port-forward와 tunnel을
수강생이 만들지 않습니다.

첫 판단 기록은 한 번만 초기화합니다.

```bash
mkdir -p artifacts/reports
test -f artifacts/reports/release-decision-record.md || \
  cp labs/release-decision-record.md \
    artifacts/reports/release-decision-record.md
```

원본 양식은 [`labs/release-decision-record.md`](release-decision-record.md),
개인 작업본은 실행 후 생성되는 `artifacts/reports/release-decision-record.md`입니다.

## 배포된 baseline 관찰

첫 판단은 데이터 EDA가 아니라 baseline identity입니다. 이 단계에서는 GET과
선언 파일 읽기만 하고 새 traffic을 만들지 않습니다.

### baseline API 응답과 선언이 같은 모델 identity를 가리키는지 판단한다

API가 응답해도 어떤 모델이 응답했는지는 별도 확인이 필요합니다. 대상 URL이
있으면 `/health/ready`와 `/v1/model`을 GET하고, 없으면
`docs/reference/evidence/incident/initial-signal.json`과 제공된 선언을 읽습니다.
실행 전에 profile, version, digest가 어떻게 대응할지 적은 뒤 결과를 확인합니다.

health 200만으로 대상 배포나 Candidate B 승인을 증명할 수 없습니다. 확인 범위
(`target`, `local`, `static`), UTC와 identity를 기록하면 이 판단을 마치고 데이터
단계로 이동합니다.

### baseline 관찰 결과가 데이터 품질 판단의 출발 근거인지 구분한다

`initial-signal.json`의 동일 100건 비교는 질문을 여는 출발 근거이지 Grafana
수집이나 새 모델 평가가 아닙니다. high-risk 비율처럼 보이는 차이를 실행 전에
예측하고, 실제 관찰, 해석, 아직 모르는 원인을
`artifacts/reports/release-decision-record.md`의 첫 행에 나누어 씁니다.

없는 대상 결과를 만들지 않고 운영 scope는 `target_pending`으로, 선언만 읽은
evidence scope는 `static`으로 유지하면 데이터 역할과 품질 근거를 확인하는 다음
단계로 넘어갑니다.

## 데이터

데이터 단계는 [1장 데이터 품질](ch01-data-quality/README.md)의 노트북과 검증
명령을 연결합니다. sealed `test`를 학습 활동에서 열지 않습니다.

### train, valid, sealed test, operational의 역할을 누수 없이 구분한다

`data/splits/physionet-2012/revisions/v2/split-manifest.csv`에서
`train 2,900 / valid 600 / test 400 / operational 100`의 역할을 읽습니다.
실행 전에 개발, 봉인 평가, 정답 없는 운영 표본의 용도를 예측하고 노트북과 분할
선언을 대조합니다. 이전 분할 `2,400 / 600 / 600 / 400`을 현재 판단에 섞지
않습니다.

### PhysioNet raw measurement의 결측, 범위, join을 데이터 품질 근거로 해석한다

`01_physionet_data_quality_eda.ipynb`를 위에서 아래로 실행해 raw measurement,
`-1` 결측 표식, 48시간 범위, outcome join, 133개 특성과 결측률을 봅니다.
IQR 범위 밖 관측을 자동 삭제하지 않고, 결측 표식이 관측 근거인지 규약 위반인지
구분해 판단 기록의 데이터 품질 칸에 기록합니다. 특성 선택과 모델 조정은 하지 않습니다.

```bash
uv run python scripts/prepare_data.py
```

원본을 재현할 수 없는 환경에서는 준비된 reference evidence만 읽고 새 수치를
만들지 않습니다.

### GE summary가 데이터 품질 관찰을 재현 가능한 evidence로 닫는지 판단한다

EDA에서 확인한 raw/processed 규칙을 다음 명령으로 검증합니다.

```bash
uv run python scripts/validate_data.py
```

실행 후 `artifacts/data-quality/great-expectations/validation-summary.json`과
Data Docs가 생성됩니다. GE 결과는 데이터 품질 근거이며 DVC 게시 차단 기준,
모델 승인 또는 target sync PASS가 아닙니다. 명령과 summary 범위를 데이터 품질 칸에
기록하고, 실행하지 못하면 evidence scope는 `offline`으로 남깁니다. 실행 자체가
막힌 경우에는 별도 execution result=`BLOCKED`와 사유, 담당자를 기록합니다. exercise의
`supports_publish_decision`은 게시 승인 결과가 아니라 이 evidence가 게시 판단을
담당할 수 있는지를 나타냅니다.

이 판단을 작은 summary 해석 exercise로 직접 닫는 흐름과 명령은
[1장 데이터 품질의 GE summary exercise](ch01-data-quality/README.md#1-3-ge-summary가-데이터-품질-관찰을-재현-가능한-evidence로-닫는지-판단한다)에 있습니다.
데이터 품질 판단을 기록한 뒤 시간이 남으면 [1장 남는 시간 실습](ch01-data-quality/README.md#2-남는-시간-실습)에서
`train`/`valid` 지문을 직접 계산합니다. 이 선택 실습은 9단계 판단을 늘리지 않습니다.

## 모델

모델 단계는 [2장 모델 품질](ch02-model-quality/README.md)로 연결합니다. 공식
봉인 결과를 다시 튜닝하지 않습니다.

### Precision, Recall, F1, FP/FN과 PR-AUC를 같은 release 질문으로 해석한다

canonical benchmark의 지표를 읽기 전에 accuracy 하나로 판단할 때 생길 오류를
예측합니다. Precision, Recall, F1, FP/FN, AUROC, PR-AUC와 threshold가 어떤
보호 질문에 답하는지 비교하고, 새 threshold나 release policy를 만들지 않습니다.

### Candidate A는 HOLD이고 Candidate B는 APPROVE인지 canonical benchmark로 판정한다

다음 명령으로 고정된 모델 상태를 확인합니다.

```bash
uv run python scripts/run_model.py status --revision v2
```

`docs/reference/evidence/model/revisions/v2/canonical-benchmark.json`과
`release-manifest.json`을 읽어 Candidate A `HOLD`, Candidate B `APPROVE`를
모델 승인으로 기록합니다. B의 승인은 대상 배포 완료가 아니며, sealed test 결과에
맞춰 특성, threshold, policy를 변경하지 않습니다.

### DVC revision과 MLflow run이 같은 model evidence lineage를 가리키는지 확인한다

`model-bootstrap.json`, `release-freeze.json`, `canonical-benchmark.json`,
`release-manifest.json`의 생성 순서와 DVC revision, dataset digest, MLflow run을
대조합니다. MLflow UI가 없으면 JSON evidence를 읽고 UI 미확인을 별도로 기록합니다.
새 공식 실행이나 model bundle을 만들지 않고 모델 품질 칸에 연결 누락을 남깁니다.
본편 판단을 닫은 뒤 시간이 남으면 [2장 남는 시간 실습](ch02-model-quality/README.md#2-남는-시간-실습)에서
임시 MLflow run만 연습합니다. 그 run은 공식 실행 번호를 대체하지 않습니다.

## API

API 단계는 [3장 서빙](ch03-serving/README.md)의 local Compose 계약을 사용합니다.
로컬 결과와 대상 결과를 섞지 않습니다.

### Compose Risk API가 정상 입력과 의도한 422를 같은 계약으로 처리하는지 확인한다

강사가 준비한 이미지를 사용해 `risk-api`만 기동합니다. 이미지 빌드는 수강생
범위가 아닙니다. `docker` 권한 오류, 이미지 없음, 모델 묶음 없음은 수강생이
고치지 않고 `API_NOT_RUNNING`과 `result=BLOCKED`로 기록합니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --no-build risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
uv run jupyter nbconvert --to notebook --execute \
  labs/ch03-serving/01_verify_risk_api.ipynb \
  --output /tmp/ch03-risk-api.ipynb \
  --ExecutePreprocessor.timeout=120
```

노트북은 정상 200과 의도한 422를 각각 한정 확인하는 bounded contract probe입니다.
실행된 `/tmp/ch03-risk-api.ipynb`에는 정상 응답의 `request_id`와
`X-Request-ID`, 의도한 422 결과가 남습니다. 실제 응답을 확인한 이 probe의
baseline scope는 `local`이며 Candidate B target 검증이 아닙니다. 이는 운영 관측
수집을 생성하는 단계가 아닙니다. API가 없으면 없는 응답을 만들지 말고
`API_NOT_RUNNING`과 `result=BLOCKED`, 사유, 담당자를 기록합니다. 준비된 자료의
evidence scope는 `static` 또는 `offline`으로, 대상 운영 scope는
`target_pending`으로 각각 남깁니다. 세 시나리오 운영 수집은 관측 조건을 먼저
고정한 뒤 4장에서 `course-session`으로 실행합니다.

### API model metadata와 bundle/deployment 선언이 같은 digest 의미를 갖는지 판단한다

`deployment.json`의 profile, version, SHA-256과 `/v1/model` 응답을 대조합니다.
이 API 단계에서는 운영 관측 수집 파일을 만들거나 읽지 않습니다. request ID와
`X-Request-ID`, 의도한 422는 `/tmp/ch03-risk-api.ipynb`의 bounded probe 결과로
확인하며, 대상 URL이 없으면 `scope=local` 또는 `scope=static` 대조만 하고
Candidate B target verified로 확장하지 않습니다. 운영 관측 수집은 4장 단계가
소유합니다.

## Kubernetes/GitOps

Kubernetes/GitOps 단계는 같은 [3장 서빙](ch03-serving/README.md)의 overlay와
배포 선언을 읽습니다. 수강생은 Application 생성, sync, path switch를 하지 않습니다.

### baseline, Candidate B, rollback overlay가 승인된 identity만 선택하는지 판단한다

overlay와 rendered manifest를 읽기 전에 선택될 identity를 예측합니다. 다음
계약 검사는 수강생이 실행할 수 있는 정적 범위입니다.

```bash
uv run pytest -q tests/integration/deployment/test_kubernetes_contract.py \
  -k candidate_and_rollback_overlays_select_only_approved_models
```

Candidate A가 overlay에 없고 승인된 identity만 선택되는지 기록합니다. 정적 검사
결과를 target sync PASS로 쓰지 않습니다.

### Argo sync, KServe health, rollback 결과를 학습자 판단 범위와 분리한다

Argo Application 생성, sync, KServe health와 rollback은 강사 Demo입니다. 후보
동기화와 되돌리기는 강사와 플랫폼 책임입니다. 수강생은
강사가 제공한 결과의 범위, 시간, identity만 기록하고 외부 인프라를 복구하지 않습니다.
결과가 없으면 운영 scope는 `target_pending`으로 남기고, sync 실행이 막힌 경우에는
별도 execution result인 `result=BLOCKED`와 사유, 담당자를 기록합니다. 정적 overlay는
`scope=static`인 복구 의도이지 rollback 완료가 아닙니다.

## 관측

관측 조건을 먼저 고정한 뒤 traffic을 실행합니다. [4장 운영 관측](ch04-observability/README.md)의
관측 수집 전에 LIVE 또는 PREPARED/OFFLINE 경로를 선택합니다.

### LIVE/PREPARED 경로와 세 신호의 상관 조건을 실행 전에 정한다

강사가 LIVE dashboard와 필요한 준비를 확인했을 때만 LIVE를 선택합니다. 그렇지
않으면 reference fixture를 사용하는 PREPARED/OFFLINE 경로를 선택합니다. 실행 전
environment, model, UTC window와 request/run/trace correlation 조건을 기록합니다.
아직 traffic을 보내지 않았으므로 log, metric, trace 결과를 이미 관찰했다고 쓰지
않습니다.

### 세 신호의 확인 범위와 상태를 traffic 실행 전에 기록 방식으로 고정한다

수집 실행 뒤 collection manifest에 기록할 `not_checked`, `unavailable`, `available`
상태와 확인 담당자를 미리 정합니다. LIVE가 아니면 fixture는 `scope=static`으로,
수집하지 않은 경로는 `offline`으로 유지합니다. secret과 token을 기록하지 않습니다.

## traffic

관측 조건을 고정한 다음 [4장 관측 수집](ch04-observability/README.md)을 실행합니다.
수집이 끝나면 같은 묶음을 개인 분석으로 넘기고, 요청 연결 확인 전까지 Compose를 내리지 않습니다.

### baseline/current-shift/invalid traffic의 의도와 상태 코드를 인계한다

LIVE 경로에서는 4장 README의 `course-session --scope local`을 한 번 실행합니다.
세 시나리오의 run ID, status code, UTC, environment와 model을 collection manifest에
남깁니다. `invalid`의 422는 입력 검증 결과이며 5xx가 아닙니다. LIVE가 없으면
`OBS-FALLBACK-02`를 `scope=static`으로 인계하고 실제 수집 결과로 바꾸지 않습니다.

### 선택한 대표 요청이 지표, 로그, trace의 동일 사건으로 연결되는지 판정한다

수집 묶음에서 normal/slow/invalid 중 하나를 고르고, 같은 run ID, request ID, trace ID를
JSONL, log event와 trace path에서 찾습니다. 새 traffic을 보내지 않습니다. offline
fixture ID는 실제 Loki/Tempo 검색으로 바꾸지 않고 `scope=static`을 유지합니다.

## 판단/rollback

판단 단계는 [5장 배포 판단](ch05-release-decision/README.md)의 최종 기록을 채웁니다.

### Candidate B 모델 APPROVE와 운영 환경 확인 상태를 한 기록에서 분리한다

모델 승인, 서빙 확인, 운영 관측을 한 기록에 모으되
`APPROVE`와 `operational_deployment_scope`를 별도 항목으로 씁니다. 대상 근거가
없으면 `target_pending`을 유지하고 local 200을 target 근거로 바꾸지 않습니다.

### rollback trigger와 baseline 복구 완료를 선언할 evidence가 있는지 판단한다

rollback overlay, target model metadata, health와 강사 smoke 결과를 구분합니다.
의도한 invalid 422나 credential 누락은 자동 rollback 조건이 아닙니다. 강사 Demo가
없으면 실제 복구 완료를 선언하지 않고 필요한 확인과 담당자를 기록합니다.

### 현재 운영 권고가 모델 승인과 분리되는지 기록한다

현재 근거 범위 안에서 유지, 보류, rollback 검토 중 하나를 권고하고, 모델 승인과
운영 권고가 다른 이유를 적습니다. 근거 목록과 교시별 기록을 사용하며 대상 확인이
없으면 권고를 `target_pending` 범위로 제한합니다.

## 회고

### 판단 기록에서 판단 변화와 미확인 위험 인계를 복원한다

`labs/release-decision-record.md`의 1일차 1부터 2일차 7까지 예상→관측→수정을 읽고
판단이 바뀐 이유를 복원합니다. 미확인 위험마다 운영 scope
(`target_pending` 또는 확인된 `target`/`local`), evidence scope (`static`/`offline`),
그리고 실행이 막힌 경우의 별도 execution result (`result=BLOCKED`, 사유, 담당자)를
각각 기록하고 필요한 자료와 재평가 조건을 남깁니다. 실행하지 않은 LIVE나 Agent
보고를 완료 근거로 쓰지 않습니다.

최종 제출에는 근거 목록, 수집 묶음 ID, 개인 분석, 대표 요청과 내일 넘길 항목을 연결합니다.
요청 연결 기록과 팀 인계를 보존한 뒤 본인이 시작했고 다른 사람이 사용하지 않는 Compose만
정리합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down
```

<a id="api-접근-계약"></a>
**API 접근 계약**

| 종류 | 값 | 수강생 |
| --- | --- | --- |
| 로컬 Compose | `http://127.0.0.1:8000` | 3장 명령으로 사용 |
| 대상 | 강사가 준 URL → `AIQA_RISK_API_URL` | GET과 기록만 수행 |
| 없음 | — | 운영 scope=`target_pending`; evidence scope=`offline` |

<a id="4gib-vm-메모리"></a>
**4GiB VM 메모리**

모든 Compose 서비스를 동시에 올리지 않습니다. 모델 단계의 `mlflow`와 API,
관측 단계의 Alloy overlay를 순서대로 사용하고, 메모리 부족 시 추가 기동을
반복하지 않고 해당 경로를 `offline`으로 닫습니다.
