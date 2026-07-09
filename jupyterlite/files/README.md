# TTA AI QA Browser Labs

이 폴더는 JupyterLite에서 바로 열 수 있는 실습 자료입니다.

브라우저 실습은 설치 없이 핵심 증거를 확인하는 경로입니다. 전체 데이터로 산출물을 다시 만들거나 서버, MLflow, Grafana, Docker 흐름을 실행하려면 원본 Jupyter 환경 또는 로컬 `labs/` 스크립트를 사용합니다.

## Notebook

| 장 | Notebook | 역할 |
| --- | --- | --- |
| 1장 | `01_data_quality/01_load_and_columns.ipynb` | 데이터 파일과 필수 컬럼 확인 |
| 1장 | `01_data_quality/02_missing_range_label.ipynb` | 결측, 범위, label 분포 확인 |
| 2장 | `02_model_quality/01_score_threshold.ipynb` | score와 threshold 흐름 확인 |
| 2장 | `02_model_quality/02_precision_recall.ipynb` | Precision과 Recall 직접 계산 |
| 2장 | `02_model_quality/03_read_metric_record.ipynb` | 준비된 metric 기록 읽기 |
| 3장 | `03_serving/01_container_basics.ipynb` | 컨테이너와 Compose 파일 존재 확인 |
| 3장 | `03_serving/02_mlflow_model_uri.ipynb` | MLflow candidate URI와 평가 기록 연결 확인 |
| 3장 | `03_serving/03_fastapi_compose_serving.ipynb` | FastAPI 요청/응답 계약을 browser fallback으로 확인 |
| 3장 | `03_serving/05_kubernetes_concepts.ipynb` | Kubernetes 핵심 개념 확인 |
| 3장 | `03_serving/06_kubernetes_mlflow_manifest.ipynb` | MLflow Kubernetes manifest 확인 |
| 3장 | `03_serving/07_argocd_kserve_manifest.ipynb` | Argo CD/KServe manifest 핵심 문자열 확인 |
| 3장 | `03_serving/08_argocd_gitops_live_check.ipynb` | live sync 확인 항목 정리 |
| 4장 | `04_observability/01_read_logs.ipynb` | JSONL 로그 필드 확인 |
| 4장 | `04_observability/02_compare_operational_numbers.ipynb` | baseline/current 운영 숫자 비교 |
| 5장 | `05_qa_strategy/01_collect_release_evidence.ipynb` | 최종 확인 report artifact 모으기 |
| 5장 | `05_qa_strategy/02_read_release_report.ipynb` | `release_approval.md` 읽기 |

## Evidence Files

- `data/`: browser execution용 소형 CSV
- `wheels/`: notebook 실행에 필요한 browser-safe helper wheel
- `artifacts/reports/`: 보고서 문장 작성에 쓰는 prepared Markdown
- `artifacts/experiments/`: 모델 평가와 비교 JSON
- `artifacts/logs/`: 운영 관측 예시 로그
- `artifacts/metrics/`: Prometheus text 예시
- `artifacts/grafana/`: dashboard JSON 예시
