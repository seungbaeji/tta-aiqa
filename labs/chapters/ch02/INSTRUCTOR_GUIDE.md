# 2장 강사용 모델 계보 가이드

이 문서는 강사가 `DVC → MLflow Run → 모델 묶음 → release manifest`를
JSON에서 읽고, 이어서 학생 MLP를 초보자용 노트북에서 직접 학습하기 위한
진행안입니다. 수강생에게 새 공식 모델을 만들게 하는 절차가 아니라, 준비된
V2 evidence와 학생 개발 실행을 구분해 읽는 수업입니다.

## 1. 강의 목표와 한 문장 설명

강의가 끝나면 다음 문장을 설명할 수 있어야 합니다.

> Git은 코드 상태, DVC와 데이터 SHA-256은 데이터 재현 상태, MLflow Run은 한
> 번의 실행, 모델 묶음은 실행 파일, release manifest는 검증된 식별값과 승인
> 결정을 연결한다.

어느 한 ID도 다른 ID를 대신하지 않습니다. 같은 profile 이름을 사용하더라도
Run, 파일, 데이터와 배포는 각각 자기 식별값으로 확인합니다.

```mermaid
flowchart LR
    G[Git commit<br/>code identity]
    D[DVC lock + dataset SHA-256<br/>data identity]
    R[MLflow model Run<br/>train/valid execution]
    B[model.joblib + metadata.json<br/>bundle identity]
    F[release freeze<br/>pre-test boundary]
    T[MLflow final Run<br/>sealed-test execution]
    M[release manifest<br/>approval linkage]
    P[runtime model SHA + image digest<br/>deployment identity]

    G --> R
    D --> R
    R --> B
    B --> F
    F --> T
    T --> M
    B --> M
    M --> P
```

## 2. 용어 기준

| 용어 | 무엇을 식별하는가 | 이 저장소의 예 | 대신할 수 없는 것 |
|---|---|---|---|
| course data revision | 과정이 정한 분할 버전 | `v2` | DVC commit이나 lock SHA |
| DVC lock SHA-256 | 구체적인 pipeline 재현 상태 | 현재 `dvc.lock` 지문 | 데이터 파일 지문 |
| dataset SHA-256 | 한 CSV의 실제 byte 내용 | train/valid/test 지문 | Run ID |
| model Run | train/valid로 모델을 만든 실행 | historical `31b50eb...` | final Run |
| final Run | frozen bundle을 sealed test로 평가한 실행 | historical `49e09d6...` | model Run |
| model bundle | 외부 runtime이 검증하고 적재할 두 파일 | `model.joblib`, `metadata.json` | MLflow Logged Model |
| MLflow Logged Model | signature와 flavor를 가진 MLflow model | 학생 Run의 `model` | release 승인 |
| release manifest | 승인 결과와 여러 식별값의 연결 문서 | `release-manifest.json` | 실제 배포 완료 |

## 3. 강의 전 준비

### 3-1. 저장소와 데이터 확인

강의 전날 저장소 루트에서 실행합니다.

```bash
uv sync --all-packages --group notebook
uv run python scripts/setup_course.py
uv run dvc status
```

`dvc status`는 `Data and pipelines are up to date.`여야 합니다. 제공 VM에
baseline bundle이 없는 경우는 학생이 해결하지 않습니다. 개인 clone에서 데이터
실습만 확인할 때는 `scripts/setup_course.py --data-only`를 사용합니다.

### 3-2. 교실 MLflow 준비

Compose `mlflow`는 local build image를 사용하므로 `--no-build` 수업 전에 강사가
한 번 빌드해야 합니다. bind mount는 container UID `65532`가 쓸 수 있게
초기화합니다. 교실 VM과 Nginx Proxy Manager는 기본 host port `5000`을
사용합니다. macOS에서 AirPlay Receiver가 5000을 점유한 로컬 리허설만
`AIQA_MLFLOW_BIND_PORT=5500`처럼 다른 port를 선택합니다.

```bash
export AIQA_MLFLOW_BIND_PORT="${AIQA_MLFLOW_BIND_PORT:-5000}"
mkdir -p artifacts/mlflow
docker compose -f deploy/compose.yaml build mlflow
docker compose -f deploy/compose.yaml run --rm --no-deps \
  --user root --entrypoint sh mlflow \
  -c 'chown -R 65532:65532 /runtime/mlflow'
docker compose -f deploy/compose.yaml up -d --no-build --wait mlflow
curl "http://127.0.0.1:${AIQA_MLFLOW_BIND_PORT}/health"
```

마지막으로 플랫폼 HTTPS 주소가 같은 server로 연결되는지 확인합니다.

```bash
export AIQA_MLFLOW_TRACKING_URI="https://mlflow-ttaN-pveX.apps.learn.mrml.dev"
curl "${AIQA_MLFLOW_TRACKING_URI%/}/health"
```

수강생은 강사가 제공한 HTTPS 주소만 사용합니다. ClusterIP, port-forward,
tunnel이나 `http://127.0.0.1:5000`을 수강생 기본 경로로 안내하지 않습니다.

## 4. 권장 강의 진행

### 4-1. 45분 진행안

| 시간 | 진행 | 강사가 닫아야 할 질문 |
|---|---|---|
| 0–5분 | 먼저 예상 | 서로 다른 ID 중 같은 값이어야 하는 것이 있는가 |
| 5–12분 | 노트북 1–2단계 | `v2`와 DVC lock SHA는 왜 다른가 |
| 12–20분 | 역사적 한계 표 | V2에서 확인한 것과 복원하지 못한 것은 무엇인가 |
| 20–27분 | bundle과 reconstruction | 일반 artifact, bundle, 공식 Run 기록을 어떻게 구분하는가 |
| 27–37분 | 학생 MLP 노트북과 UI | 손실은 내려가는데 검증은 왜 멈출 수 있는가 |
| 37–42분 | 정상 lifecycle 코드 | freeze 전후로 model Run과 final Run이 왜 나뉘는가 |
| 42–45분 | Teach-back | 수강생이 전체 연결을 자기 문장으로 설명할 수 있는가 |

### 4-2. 실행 명령

```bash
uv run jupyter nbconvert --to notebook --execute \
  labs/chapters/ch02/02_trace_model_lineage.ipynb \
  --output /tmp/ch02-model-lineage.ipynb \
  --ExecutePreprocessor.timeout=600
uv run jupyter nbconvert --to notebook --execute \
  labs/chapters/ch02/03_log_student_mlp.ipynb \
  --output /tmp/ch02-student-mlp.ipynb \
  --ExecutePreprocessor.timeout=600
```

노트북을 대화형으로 열 때도 셀 순서를 바꾸지 않습니다. `02`는 공식 JSON만
읽습니다. `03`에서 학습/검증 파일이 없으면 `prepare_data.py`를 먼저
실행합니다. `MLFLOW_NOT_RUNNING`이면 표와 그림, 정적 evidence까지는 설명할
수 있지만 MLflow UI 관찰은 완료한 것이 아닙니다.

## 5. 역사적 V2와 정상 lifecycle

### 5-1. 역사적 V2에서 말할 수 있는 것

다음은 지문으로 대조돼 있습니다.

- train, valid와 sealed test CSV의 SHA-256
- Candidate B의 canonical metric과 `APPROVE` 결정
- `model.joblib`, `metadata.json`의 SHA-256
- 기록된 model Run ID와 final Run ID
- 승인 profile과 feature contract SHA-256

### 5-2. 역사적 V2에서 말하면 안 되는 것

다음 세 DVC lock 지문은 서로 다릅니다.

- 현재 repository `dvc.lock`
- `split-revision.json`에 기록된 V2 분할 당시 lock
- `model-bootstrap.json`에 기록된 역사적 모델 생성 당시 lock

원본 frozen lock blob은 저장소에 없고 역사적 model bootstrap은 dirty Git
worktree를 기록합니다. 따라서 “과거 DVC pipeline과 MLflow Run을 완전
재현했다”고 말하지 않습니다. 정확한 표현은 “보존된 데이터·metric·bundle
지문을 사후 reconciliation했다”입니다.

역사적 manifest 내부의 `reference/evidence/...` 경로는 평탄화 이전 portable
경로입니다. 현재 읽기 위치는 `docs/evidence/...`이며, 과거 evidence를 새 경로로
보이게 하려고 원본 JSON을 수정하지 않습니다. 개인 clone에 역사적 bundle
파일이 없을 수도 있으므로 JSON의 SHA-256 확인과 실제 파일 적재 확인도
구분합니다.

### 5-3. 새 revision의 정상 순서

1. Git에 versioned code와 YAML을 기록합니다.
2. DVC pipeline으로 역할별 데이터를 만들고 lock과 데이터 지문을 검토합니다.
3. train/valid만 사용해 후보를 비교합니다.
4. model Run, model bundle과 provenance를 기록합니다.
5. clean Git 상태에서 `release-freeze.json`을 먼저 고정합니다.
6. frozen bundle로 sealed test를 한 번만 평가하고 final Run을 기록합니다.
7. `release-manifest.json`에 승인 profile, 두 Run ID와 파일 지문을 연결합니다.
8. 배포 후 runtime model SHA-256과 immutable image digest를 다시 대조합니다.

V2 historical evidence를 다시 실행하는 대신 새 revision 번호로 이 lifecycle을
시작해야 합니다.

## 6. MLflow 화면과 코드

### 6-1. 화면을 읽는 순서

1. Experiment가 `student-development-tracking`인지 확인합니다. MLflow 3 UI
   왼쪽의 `GenAI`가 켜져 있으면 `Model training`으로 바꿉니다. `Default`
   experiment의 Overview/Models는 학생 학습 Run이 아닙니다. 이 화면은
   `03_log_student_mlp.ipynb`를 실행한 뒤에 엽니다.
2. Run tag의 `not_official_evidence=true`와 `aiqa.profile=candidate-c`를 봅니다.
3. Parameters에서 `model_kind=mlp_classifier`, `max_iter`, `train_data_hash`,
   `valid_data_hash`를 확인합니다.
4. Metrics에서 `train.loss`와 `valid.roc_auc`가 iteration `step`으로 보이는지
   확인합니다. `train.loss`가 내려가는데 `valid.roc_auc`가 평평하거나 나빠지면
   과적합입니다. 공식 승인은 Candidate B입니다.
5. Logged Models에서 sklearn flavor로 올라간 model을 봅니다.
6. 학생 노트북은 Datasets `log_input`이나 `bundle/model.joblib`을 올리지
   않습니다. 파일 지문은 Parameters의 64자리 SHA-256입니다. 공식 Candidate B
   bundle은 `02_trace_model_lineage.ipynb`의 JSON에서 읽습니다.

### 6-2. 화면과 구현 연결

학생 Run은 `03_log_student_mlp.ipynb`의 `mlflow.set_tags`, `mlflow.log_params`,
`mlflow.log_metric(..., step=)`, `mlflow.sklearn.log_model()`이 만듭니다.
공식 trainer의 dataset input, bundle artifact, registry 부재는 02 노트북의
코드 표와 아래 패키지에서 읽습니다.

현재 코드는 `register_model()`이나 `registered_model_name`을 사용하지 않으므로
Model Registry version/alias 등록은 하지 않습니다. `Logged Models`와 `Model
Registry`를 같은 기능으로 설명하지 않습니다. 이 과정의 공식 승인 source of
truth는 immutable bundle SHA-256과 `release-manifest.json`입니다.

학생 client는 `artifacts/mlflow/`에 직접 파일을 쓰지 않습니다. 하지만 Compose
MLflow server는 받은 Run metadata와 artifact를 그 host bind mount에
지속합니다. “client write boundary”와 “server persistence boundary”를 구분해
설명합니다.

## 7. 코드 읽기 순서

1. `dvc.yaml`, `dvc.lock`, `docs/evidence/data-v2/split-revision.json`
2. `labs/run/development.yaml`, `configs/model-v2/student-profiles.yaml`
3. `labs/chapters/ch02/03_log_student_mlp.ipynb`
4. `packages/aiqa_model/adapters/mlflow/runtime.py::configure_tracking`
5. `packages/aiqa_model/adapters/mlflow/model.py::MlflowModelTracker.record`
6. `packages/aiqa_model/adapters/bundles/joblib.py::persist_model_bundle`
7. `apps/model_trainer/application/bundles.py::bootstrap_models`
8. `apps/model_trainer/application/finalization.py::run_final`
9. `apps/model_trainer/adapters/release_provenance.py`

처음 세 항목은 학생이 YAML·pandas·sklearn·mlflow로 직접 보는 개발 실행입니다.
그 다음 항목은 공식 trainer가 같은 화면 값을 어떻게 남기는지 읽는 코드입니다.
마지막 세 항목은 새 공식 revision의 freeze, sealed evaluation과 manifest
lifecycle을 설명합니다.

## 8. 문제 해결

| 증상 | 의미 | 확인 순서 |
|---|---|---|
| `FileNotFoundError` | 역할별 입력 파일 없음 | `prepare_data.py` 실행 후 `dvc status` |
| SHA-256 assert 실패 | 입력이 V2 evidence와 달라짐 | 파일을 임의 수정하지 말고 DVC 재현 상태 확인 |
| `MLFLOW_NOT_RUNNING` | URI 없음 또는 `/health` 실패 | 환경 변수, DNS/TLS, proxy와 server health |
| UI가 permission 또는 Failed to load chart data | 공개 HTTPS Origin의 POST가 CORS 403 | server log의 `Blocked cross-origin request`, `--cors-allowed-origins *` |
| `Default` Overview/Models만 보임 | GenAI 화면이거나 잘못된 experiment | `Model training`과 `student-development-tracking` |
| SQLite permission error | server bind mount 쓰기 불가 | 강의 전 `chown` 초기화 재실행 |
| 학생 Run에 bundle이 없음 | 학생 노트북은 bundle을 올리지 않음 | 공식 bundle은 lineage JSON으로 설명 |
| 공식 historical Run이 UI에 없음 | 과거 server가 현재 교실 server가 아님 | 정적 evidence reconstruction으로만 설명 |

강의 종료 후 다른 Compose 실습과 자원을 격리하려면 다음 명령을 실행합니다.

```bash
docker compose -f deploy/compose.yaml stop mlflow
```

## 9. Teach-back 점검

강사와 수강생이 문서를 보지 않고 다음 질문에 답하면 이 단계를 완료합니다.

1. course data revision과 DVC lock SHA-256의 차이는 무엇인가.
2. V2 historical evidence에서 확인된 연결과 복원 불가능한 범위는 무엇인가.
3. model Run과 final Run은 왜 분리되는가.
4. model bundle과 MLflow Logged Model은 왜 둘 다 기록하는가.
5. 학생 MLP 노트북에서 train/valid SHA-256을 확인한 뒤 같은 파일로 학습하는가.
6. release manifest가 있어도 실제 배포 완료를 별도로 확인하는 이유는 무엇인가.

정답은 각각 “이름과 구체 상태”, “reconciliation boundary”, “개발과 봉인 평가”,
“외부 runtime과 MLflow contract”, “같은 CSV 지문”, “승인과
runtime state의 분리”를 포함해야 합니다.

## 10. 도입 체크리스트

다른 프로젝트에 적용할 때 다음 항목을 먼저 설계합니다.

- 데이터 역할과 누수 금지 규칙을 versioned contract로 소유하는가.
- DVC stage가 실제 code, config, parameter와 input만 dependency로 선언하는가.
- 학습에 사용한 파일과 MLflow dataset input이 동일한가.
- parameter, metric, tag와 artifact 이름을 contract로 관리하는가.
- model bundle에 model, metadata, feature contract와 provenance가 연결되는가.
- sealed test 전에 immutable freeze가 존재하는가.
- model Run과 final Run을 별도 ID로 기록하는가.
- manifest가 승인 profile과 모든 immutable digest를 연결하는가.
- 배포가 mutable tag가 아니라 image와 model digest로 식별되는가.
- 실행할 수 없는 외부 검증을 `pending`으로 사실대로 기록하는가.
