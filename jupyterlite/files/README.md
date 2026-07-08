# TTA AI QA Browser Labs

이 폴더는 JupyterLite에서 바로 열 수 있는 실습 자료입니다.

브라우저 실습은 설치 없이 핵심 증거를 확인하는 경로입니다. 전체 데이터로 산출물을 다시 만들거나 서버, MLflow, Grafana, Docker 흐름을 실행하려면 원본 Jupyter 환경 또는 로컬 `labs/` 스크립트를 사용합니다.

## Notebook

| 장 | Notebook | 역할 |
| --- | --- | --- |
| 1장 | `01_data_quality/1_pandas_data_quality_lab.ipynb` | 기준 데이터 품질 확인 |
| 2장 | `02_model_quality/0_great_expectations_artifact_lab.ipynb` | GE prepared artifact 읽기 |
| 2장 | `02_model_quality/1_model_evaluation_lab.ipynb` | 모델 지표와 threshold 해석 |
| 2장 | `02_model_quality/2_data_metric_connection_lab.ipynb` | 데이터 조건 변화와 지표 변화 연결 |
| 3장 | `03_serving/fastapi_serving_lab.ipynb` | API 계약과 응답 필드 확인 |
| 4장 | `04_observability/observability_lab.ipynb` | 로그와 메트릭 기반 운영 관측 |
| 5장 | `05_qa_strategy/qa_strategy_lab.ipynb` | drift, 원인 후보, release gate 판단 |

## Evidence Files

- `data/`: browser execution용 소형 CSV
- `wheels/`: notebook 실행에 필요한 browser-safe helper wheel
- `artifacts/reports/`: 보고서 문장 작성에 쓰는 prepared Markdown
- `artifacts/experiments/`: 모델 평가와 비교 JSON
- `artifacts/logs/`: 운영 관측 예시 로그
- `artifacts/metrics/`: Prometheus text 예시
- `artifacts/grafana/`: dashboard JSON 예시
