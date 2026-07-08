# AI 품질 관리와 운영 관측 실습 Repository

이 repository는 수강생이 2일 과정에서 직접 열고 실행하거나 확인하는 실습 작업 공간입니다. 온라인 교재와 슬라이드에서 안내하는 경로를 그대로 유지해, 교재의 명령과 artifact 경로가 이 repository에서도 같은 의미를 갖도록 구성합니다.

## 1. 온라인 자료

온라인 교재와 JupyterLite는 별도로 제공합니다.

| 자료        | URL                                        |
| ----------- | ------------------------------------------ |
| 교재 사이트 | <https://aiqa.learn.mrml.dev>              |
| JupyterLite | <https://aiqa.learn.mrml.dev/jupyterlite/> |

로컬 repository는 실습 파일과 산출물 기록을 위한 공간입니다. 개념 설명은 교재 사이트를 기준으로 확인합니다.

## 2. 준비

Python 3.11을 기준으로 실습합니다. 이 repository에는 `.python-version`을 3.11로 두어 `uv`가 같은 Python 계열을 우선 사용하도록 합니다. `uv`는 Astral에서 제공하는 Python package/project manager입니다. 설치 파일과 자세한 안내는 [공식 설치 문서](https://docs.astral.sh/uv/getting-started/installation/)에서 확인합니다.

### 2-1. uv 설치

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS 또는 Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 후 새 터미널을 열고 확인합니다.

```bash
uv --version
```

Python 3.11이 없으면 `uv`로 설치합니다.

```bash
uv python install 3.11
```

### 2-2. 의존성 설치

Windows, macOS, Linux 공통:

```bash
uv sync --group lab --group demo --group dev
```

Docker, Kubernetes, MLflow, Grafana는 모든 수강생이 직접 운영하지 않아도 됩니다. 서버나 외부 런타임이 필요한 내용은 준비된 artifact를 먼저 확인하고, 가능한 환경에서만 로컬 재생성을 진행합니다.

## 3. 첫 확인

Windows, macOS, Linux 공통:

```bash
uv run python scripts/course.py smoke
```

`smoke`는 교재에서 참조하는 기본 폴더가 있는지만 확인합니다. 모델 품질이나 운영 품질 결론을 만들지는 않습니다.

## 4. 실습 데이터와 산출물 준비

root `data/`에는 원본 CSV인 `data/human_vital_signs_dataset_2024.csv`만 Git에 포함합니다. 장별 실습에서 사용하는 파생 CSV/JSONL은 원본에서 다시 생성합니다.

### 4-1. 데이터 생성

```bash
uv run python scripts/course.py prepare-data
```

위 명령은 다음 직접 실행 명령과 같습니다.

```bash
uv run python labs/prepare_data.py
```

생성되는 root `data/` 파생 파일은 로컬 실습 준비물이며 Git에는 커밋하지 않습니다.

### 4-2. 전체 산출물 재생성

전체 lab 산출물까지 한 번에 재생성하려면 다음 명령을 사용합니다.

```bash
uv run python scripts/course.py labs
```

이 명령은 `artifacts/` 아래 prepared evidence도 다시 씁니다. 수강생이 “준비된 artifact 확인”만 한 경우와 “로컬에서 재생성”한 경우를 보고서에 구분해서 적어야 합니다.

장별로 확인하려면 다음 명령을 하나씩 실행합니다.

| 장 | wrapper 명령 | 실제 실행되는 Python script | 주요 산출물 |
| --- | --- | --- | --- |
| 1장 | `uv run python scripts/course.py lab-data-quality` | `uv run python labs/ch01_data_quality/build_quality_report.py` | `artifacts/reports/chapter_01_quality_report.md` |
| 2장 | `uv run python scripts/course.py lab-model-quality` | 아래 2장 script 3개를 순서대로 실행 | `artifacts/models/chapter_02_baseline.pkl`, `artifacts/experiments/chapter_02/*.json`, `artifacts/reports/chapter_02_model_quality_comparison.md` |
| 3장 | `uv run python scripts/course.py lab-serving` | `uv run python labs/ch03_serving/check_serving_contract.py` | `outputs/check_serving_contract_prediction_events.jsonl` |
| 4장 | `uv run python scripts/course.py lab-observability` | `uv run python labs/ch04_observability/build_observability_artifacts.py` | `artifacts/logs/*.jsonl`, `artifacts/metrics/chapter_04_anomaly.prom`, `artifacts/grafana/*.json`, `artifacts/reports/quality_issue_trace.md` |
| 5장 | `uv run python scripts/course.py lab-qa-strategy` | `uv run python labs/ch05_qa_strategy/build_qa_artifacts.py` | `artifacts/reports/drift_report.md`, `release_approval.md`, `ai_qa_checklist.md` |

### 4-3. 실행 후 정리

로컬 생성 데이터와 runtime output을 지우려면 다음 명령을 실행합니다.

```bash
uv run python scripts/course.py clean-data
uv run python scripts/course.py clean
```

prepared artifact를 강의 배포 상태로 되돌리려면 Git 기준으로 복구합니다.

```bash
git restore artifacts
```

## 5. Repository 구성

| 경로                         | 역할                                                        |
| ---------------------------- | ----------------------------------------------------------- |
| `labs/`                      | 장별 로컬 notebook, Python script, 실습 보조 설명           |
| `jupyterlite/files/`         | 브라우저 실행용 notebook, 소형 데이터, prepared evidence    |
| `data/`                      | 교재와 실습에서 참조하는 CSV 데이터                         |
| `artifacts/`                 | 리포트, 실험 기록, 로그, metric, dashboard evidence         |
| `configs/`                   | validation, lineage, 운영, QA 판단 기준 설정                |
| `packages/ai-quality/`       | lab script와 notebook이 사용하는 공통 교육용 Python package |
| `demos/`                     | Docker, MLflow, Grafana 같은 로컬 demo 보조 자료            |
| `docs/materials-manifest.md` | 강의 제작 repository에서 옮긴 자료의 포함/제외 기준         |

## 6. 실습 순서

실습은 온라인 교재의 개념 설명을 읽은 뒤, `labs/`의 notebook으로 판단 흐름을 따라가고, 필요한 경우 Python script로 같은 evidence를 로컬에서 재생성하는 순서로 진행합니다. Notebook은 해석과 중간 출력을 확인하는 주 실습 자료이고, Python script는 전체 데이터 기준 산출물을 다시 만드는 재현 경로입니다.

로컬에서 notebook을 열어 따라가려면 먼저 Jupyter Lab을 실행합니다.

```bash
uv run jupyter lab
```

### 6-1. 공통 준비

모든 장별 실습 전에 repository 구조와 파생 데이터를 준비합니다.

| 순서 | 작업 | 명령 또는 파일 | 확인할 것 |
| --- | --- | --- | --- |
| 1 | 환경 설치 | `uv sync --group lab --group demo --group dev` | `.venv`가 생성되고 의존성이 설치되는지 확인 |
| 2 | 구조 확인 | `uv run python scripts/course.py smoke` | `student repo structure is ready` 출력 |
| 3 | 파생 데이터 생성 | `uv run python scripts/course.py prepare-data` | `data/vital_signs_train.csv`, `data/serving_requests_valid.csv` 등 생성 |
| 4 | 전체 흐름 선택 | Jupyter Lab 또는 장별 CLI | notebook 확인인지 로컬 재생성인지 구분 |

`scripts/course.py`는 수강생이 외울 실행 파일이 아니라, Windows/macOS/Linux에서 같은 명령으로 장별 script를 호출하기 위한 wrapper입니다. 실제 코드를 직접 실행하려면 `uv run python labs/.../*.py` 형태를 사용합니다. 두 방식은 같은 Python 환경과 같은 repository 경로에서 실행됩니다.

### 6-2. 1장 데이터 품질

모델 평가 전에 데이터가 평가 가능한 구조인지 확인합니다.

| 순서 | 따라갈 코드 | 역할 |
| --- | --- | --- |
| 1 | `labs/ch01_data_quality/1_pandas_data_quality_lab.ipynb` | 데이터 로딩, schema, 결측, 범위, label 분포를 셀 단위로 확인 |
| 2 | `labs/ch01_data_quality/utils.py` | notebook에서 쓰는 1장 helper의 책임 확인 |
| 3 | `labs/ch01_data_quality/build_quality_report.py` | 전체 데이터 기준 품질 리포트 재생성 |
| 4 | `artifacts/reports/chapter_01_quality_report.md` | 데이터 품질 판단 문장 확인 |

CLI로 재생성할 때는 실제 script를 직접 실행합니다.

```bash
uv run python labs/ch01_data_quality/build_quality_report.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-data-quality
```

### 6-3. 2장 모델 품질

데이터 품질 전제가 모델 지표와 어떻게 연결되는지 확인합니다. 2장은 notebook과 script가 여러 개이므로 아래 순서대로 진행합니다.

| 순서 | 따라갈 코드 | 역할 |
| --- | --- | --- |
| 1 | `labs/ch02_model_quality/README.md` | 2장 모델 평가와 데이터-지표 연결 실습의 전체 흐름 확인 |
| 2 | `labs/ch02_model_quality/3_model_evaluation_lab.ipynb` | test 데이터에서 score, prediction, confusion matrix, metric 해석 |
| 3 | `labs/ch02_model_quality/2_great_expectations_lab.ipynb` | degraded validation 데이터의 검증 실패를 prepared artifact와 연결 |
| 4 | `labs/ch02_model_quality/4_data_metric_connection_lab.ipynb` | 데이터 품질 신호와 metric 변화가 같은 사건인지 확인 |
| 5 | `labs/ch02_model_quality/5_mlflow_tracking_lab.ipynb` | 로컬 평가 기록과 MLflow/JSON 기록 범위 확인 |
| 6 | `labs/ch02_model_quality/train_baseline.py` | 기준 모델 재학습 |
| 7 | `labs/ch02_model_quality/evaluate_and_record.py` | test 평가와 experiment JSON/MLflow 기록 생성 |
| 8 | `labs/ch02_model_quality/build_comparison_artifacts.py` | baseline/degraded/test 비교 artifact와 보고서 생성 |
| 9 | `artifacts/reports/chapter_02_model_quality_comparison.md` | 최종 모델 품질 비교 판단 확인 |

2장 CLI 재생성은 script 3개를 순서대로 직접 실행합니다.

```bash
uv run python labs/ch02_model_quality/train_baseline.py
uv run python labs/ch02_model_quality/evaluate_and_record.py
uv run python labs/ch02_model_quality/build_comparison_artifacts.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-model-quality
```

### 6-4. 3장 서빙 계약

예측 API가 단순히 score를 반환하는지보다, 요청/응답 계약이 추적 가능한 evidence를 남기는지 확인합니다.

| 순서 | 따라갈 코드 | 역할 |
| --- | --- | --- |
| 1 | `labs/ch03_serving/README.md` | FastAPI serving 구조, 계약 확인 기준, train-serving skew 의미 확인 |
| 2 | `labs/ch03_serving/fastapi_serving_lab.ipynb` | 요청 payload, 응답 schema, validation failure, train-serving skew 확인 |
| 3 | `labs/ch03_serving/check_serving_contract.py` | API 계약 자동 확인 |
| 4 | `outputs/check_serving_contract_prediction_events.jsonl` | 계약 확인 중 생성된 prediction event 확인 |

CLI로 확인할 때는 실제 script를 직접 실행합니다.

```bash
uv run python labs/ch03_serving/check_serving_contract.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-serving
```

### 6-5. 4장 운영 관측

운영 로그, metric, dashboard JSON을 연결해 모델 평가만으로 설명되지 않는 운영 품질 신호를 확인합니다.

| 순서 | 따라갈 코드 | 역할 |
| --- | --- | --- |
| 1 | `labs/ch04_observability/observability_lab.ipynb` | structured log, request trace, Prometheus metric, dashboard panel을 순서대로 확인 |
| 2 | `labs/ch04_observability/build_observability_artifacts.py` | 로그, metric, Grafana payload, issue trace 재생성 |
| 3 | `artifacts/logs/chapter_04_normal_events.jsonl` | baseline 운영 이벤트 확인 |
| 4 | `artifacts/logs/chapter_04_anomaly_events.jsonl` | current/anomaly 운영 이벤트 확인 |
| 5 | `artifacts/metrics/chapter_04_anomaly.prom` | Prometheus metric 확인 |
| 6 | `artifacts/grafana/*.json` | dashboard panel과 Grafana Cloud payload preview 확인 |
| 7 | `artifacts/reports/quality_issue_trace.md` | 관측 신호를 owner와 next action으로 연결 |

CLI로 재생성할 때는 실제 script를 직접 실행합니다.

```bash
uv run python labs/ch04_observability/build_observability_artifacts.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-observability
```

### 6-6. 5장 QA 전략

앞 장에서 만든 데이터 품질, 모델 품질, serving, observability evidence를 release 판단으로 묶습니다.

| 순서 | 따라갈 코드 | 역할 |
| --- | --- | --- |
| 1 | `labs/ch05_qa_strategy/README.md` | input drift, score/prediction 분포, incident trace, release criteria, checklist 기준 확인 |
| 2 | `labs/ch05_qa_strategy/qa_strategy_lab.ipynb` | drift, score 분포, incident trace, release criteria를 하나의 판단 흐름으로 연결 |
| 3 | `labs/ch05_qa_strategy/build_qa_artifacts.py` | QA 전략 리포트와 checklist 재생성 |
| 4 | `artifacts/reports/release_approval.md`, `artifacts/reports/ai_qa_checklist.md` | 최종 판단 문서 확인 |

CLI로 재생성할 때는 실제 script를 직접 실행합니다.

```bash
uv run python labs/ch05_qa_strategy/build_qa_artifacts.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-qa-strategy
```

### 6-7. 전체 재생성 순서

장별 script를 한 번에 실행할 때의 내부 순서는 다음과 같습니다.

| 순서 | 직접 실행 명령 | 생성 또는 갱신되는 주요 경로 |
| --- | --- | --- |
| 1 | `uv run python labs/prepare_data.py` | `data/vital_signs*.csv`, `data/serving_requests*.csv`, `data/*events.jsonl` |
| 2 | `uv run python labs/ch01_data_quality/build_quality_report.py` | `artifacts/reports/chapter_01_quality_report.md` |
| 3 | `uv run python labs/ch02_model_quality/train_baseline.py` | `artifacts/models/chapter_02_baseline.pkl` |
| 4 | `uv run python labs/ch02_model_quality/evaluate_and_record.py` | `artifacts/experiments/chapter_02/model_test_eval.json`, `artifacts/mlflow.db` |
| 5 | `uv run python labs/ch02_model_quality/build_comparison_artifacts.py` | `artifacts/experiments/chapter_02/validation_degradation_comparison.json`, `artifacts/reports/chapter_02_model_quality_comparison.md` |
| 6 | `uv run python labs/ch03_serving/check_serving_contract.py` | `outputs/check_serving_contract_prediction_events.jsonl` |
| 7 | `uv run python labs/ch04_observability/build_observability_artifacts.py` | `artifacts/logs/`, `artifacts/metrics/`, `artifacts/grafana/`, `artifacts/reports/quality_issue_trace.md` |
| 8 | `uv run python labs/ch05_qa_strategy/build_qa_artifacts.py` | `artifacts/reports/drift_report.md`, `release_approval.md`, `ai_qa_checklist.md` |

전체 순서를 wrapper로 한 번에 실행하려면 다음 명령을 사용합니다.

```bash
uv run python scripts/course.py labs
```

### 6-8. 실습 후 확인과 정리

로컬 재생성 후에는 어떤 파일을 근거로 판단했는지 먼저 확인합니다.

```bash
git status --short
```

보고서에는 `artifacts/reports/` 아래 파일 경로와 실행 범위를 함께 적습니다. 로컬 생성 파일을 지우려면 다음 명령을 실행합니다.

```bash
uv run python scripts/course.py clean-data
uv run python scripts/course.py clean
```

prepared artifact를 배포 상태로 되돌리려면 다음 명령을 사용합니다.

```bash
git restore artifacts
```

## 7. 실습 경로 구분

이 과정에는 두 가지 실행 경로가 있습니다.

| 경로                   | 목적                                        | 보고서에 쓰는 표현                  |
| ---------------------- | ------------------------------------------- | ----------------------------------- |
| Prepared artifact 확인 | 이미 생성된 리포트와 로그를 읽고 판단 작성  | prepared artifact에서 확인          |
| Local 재생성           | Python script로 데이터와 산출물을 다시 생성 | 로컬에서 재생성한 artifact에서 확인 |

JupyterLite 또는 prepared artifact만 확인했다면 전체 데이터를 직접 재생성했다고 쓰지 않습니다. 반대로 로컬 script를 실행했다면 실행 시점과 생성 파일 경로를 함께 남깁니다.

## 8. 보고서 작성 원칙

보고서에는 다음 네 가지를 구분해 남깁니다.

| 항목      | 예시                                                       |
| --------- | ---------------------------------------------------------- |
| 근거 위치 | `artifacts/reports/chapter_02_model_quality_comparison.md` |
| 실행 범위 | 준비된 artifact 확인 또는 로컬 재생성                      |
| 판단      | 승인, 조건부 보류, 추가 확인                               |
| 다음 확인 | 담당 영역과 재평가 조건                                    |

## 9. 기본 명령

```bash
uv sync --group lab --group demo --group dev
uv run python scripts/course.py smoke
uv run python scripts/course.py prepare-data
uv run python scripts/course.py labs
```

macOS나 Linux에서 `make`를 사용할 수 있다면 같은 작업을 `make setup`, `make smoke`, `make labs`로 실행해도 됩니다. Windows에서는 `uv run python scripts/course.py ...` 명령을 기준으로 진행합니다.

장별 실습은 온라인 교재의 순서에 맞춰 진행합니다.
