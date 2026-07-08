# Labs

이 디렉터리는 실습 안내, Notebook, 그리고 실습 준비용 Python program을 함께 관리합니다. `docs/`가 강의 교재 사이트라면, `labs/`는 수강생이 실제로 열고 실행하는 실습 작업 공간입니다.

| 장 | Lab 문서 | Notebook | Python program |
| --- | --- | --- | --- |
| 1장 데이터 품질 | `ch01_data_quality/README.md` | `ch01_data_quality/pandas_data_quality_lab.ipynb` | `ch01_data_quality/build_quality_report.py` |
| 2장 모델 품질 | `ch02_model_quality/README.md` | `ch02_model_quality/model_evaluation_lab.ipynb`, `ch02_model_quality/data_metric_connection_lab.ipynb` | `ch02_model_quality/train_baseline.py`, `ch02_model_quality/evaluate_and_record.py`, `ch02_model_quality/build_comparison_artifacts.py` |
| 3장 서빙 | `ch03_serving/README.md` | `ch03_serving/fastapi_serving_lab.ipynb` | `ch03_serving/check_serving_contract.py` |
| 4장 운영 관측 | `ch04_observability/README.md` | `ch04_observability/observability_lab.ipynb` | `ch04_observability/build_observability_artifacts.py` |
| 5장 QA 전략 | `ch05_qa_strategy/README.md` | `ch05_qa_strategy/qa_strategy_lab.ipynb` | `ch05_qa_strategy/build_qa_artifacts.py` |

Notebook은 수강생이 중간 출력과 QA 해석을 확인하는 주 실습 자료입니다. 각 Notebook은 JupyterLite에서도 실행되도록 로컬 패키지 import, 서버 실행, pickle 모델 로딩 없이 브라우저 안의 소형 실습 샘플과 미니 계산 함수로 구성합니다. Python program은 같은 판단 흐름을 전체 데이터와 저장소 공통 코드로 재생성하고, 모델 파일, 품질 리포트, 로그, 메트릭, Grafana dashboard, QA checklist 같은 산출물을 만들거나 계약 검증을 자동화할 때 사용합니다.

## 실행 경로

실습에는 두 가지 경로가 있습니다. 수강생이 보고서 근거를 빠르게 확인하는 경로와 강사나 검증자가 전체 데이터를 기준으로 산출물을 다시 만드는 경로를 구분해야 합니다.

| 경로 | 목적 | 필요한 자료 | 보고서 표현 |
| --- | --- | --- | --- |
| Prepared artifact 확인 | 이미 생성된 리포트, 로그, 메트릭, checklist를 읽고 판단 작성 | `artifacts/`, JupyterLite files | “준비된 artifact에서 확인했습니다” |
| 전체 재생성 | 원본 CSV에서 파생 데이터와 Lab 산출물을 다시 생성 | `data/human_vital_signs_dataset_2024.csv` | “로컬에서 재생성한 artifact에서 확인했습니다” |

## Python program 직접 실행 순서

`scripts/course.py`는 아래 script를 순서대로 호출하는 wrapper입니다. 수강생이 파일 역할을 확인하면서 실행할 때는 다음 명령을 직접 사용합니다.

| 순서 | 명령 | 역할 |
| --- | --- | --- |
| 1 | `uv run python labs/prepare_data.py` | 원본 CSV에서 장별 파생 데이터 생성 |
| 2 | `uv run python labs/ch01_data_quality/build_quality_report.py` | 1장 데이터 품질 리포트 생성 |
| 3 | `uv run python labs/ch02_model_quality/train_baseline.py` | 2장 기준 모델 학습 |
| 4 | `uv run python labs/ch02_model_quality/evaluate_and_record.py` | 2장 test 평가와 experiment 기록 생성 |
| 5 | `uv run python labs/ch02_model_quality/build_comparison_artifacts.py` | 2장 validation degradation 비교 리포트 생성 |
| 6 | `uv run python labs/ch03_serving/check_serving_contract.py` | 3장 API 요청/응답 계약 확인 |
| 7 | `uv run python labs/ch04_observability/build_observability_artifacts.py` | 4장 로그, metric, dashboard evidence 생성 |
| 8 | `uv run python labs/ch05_qa_strategy/build_qa_artifacts.py` | 5장 drift, release, QA checklist 산출물 생성 |

전체 실습 산출물을 한 번에 다시 만들려면 원본 CSV가 준비된 상태에서 다음 wrapper 명령을 실행합니다. 원본 CSV가 없으면 먼저 멈추고 prepared artifact 확인 경로를 안내합니다.

```bash
uv run python scripts/course.py labs
```

원본 CSV만 준비되어 있고 파생 CSV가 없는 환경에서는 wrapper가 먼저 `labs/prepare_data.py`를 실행합니다. 이 단계는 `data/vital_signs_train.csv`, `data/vital_signs_valid_baseline.csv`, `data/vital_signs_valid_degraded.csv`, `data/vital_signs_test.csv` 같은 실습용 데이터를 다시 만듭니다.

보고서에는 실행 범위를 반드시 구분합니다. JupyterLite나 prepared artifact만 확인했다면 전체 데이터와 전체 산출물을 직접 재생성했다고 쓰지 않습니다. 반대로 Python program을 성공적으로 실행했다면 재생성한 artifact 경로와 실행 시점을 함께 남겨 reviewer가 같은 근거를 추적할 수 있게 합니다.
