# Notebook Structure

이 문서는 수강생이 먼저 실행할 초급 notebook 경로를 정의합니다. 기존 긴 notebook은 참고용으로 남기고, 수업 중 직접 따라 하는 기본 경로는 아래 파일을 우선 사용합니다.

## 작성 원칙

| 원칙 | 기준 |
| --- | --- |
| 한 notebook 한 목표 | 파일 열기, 결측 확인, metric 계산처럼 하나의 작은 목표만 둡니다 |
| 코드 셀 짧게 유지 | 일반 코드 셀은 3~8줄을 우선하고, 긴 반복 로직은 피합니다 |
| 함수 정의 최소화 | 수강생이 따라 써야 하는 셀에는 `def`, 복잡한 parser, nested loop를 넣지 않습니다 |
| 출력은 관측값 중심 | 코드가 결론 문장을 대신 만들지 않고, 표와 숫자를 보여 줍니다 |
| helper는 준비용만 | JupyterLite 준비, 파일 복사, sample fallback 같은 비핵심 로직만 `utils.py`에 둡니다 |
| Markdown이 해석 담당 | 코드 다음 Markdown에서 관측값을 어떻게 읽을지 설명합니다 |

## 기본 노트북 경로

| Chapter | Notebook | 목표 |
| --- | --- | --- |
| 1장 | `labs/ch01_data_quality/01_load_and_columns.ipynb` | 평가 데이터 파일을 열고 필수 컬럼 존재를 확인합니다 |
| 1장 | `labs/ch01_data_quality/02_missing_range_label.ipynb` | 결측, 범위, label 분포를 작은 표로 확인합니다 |
| 2장 | `labs/ch02_model_quality/01_score_threshold.ipynb` | score와 threshold가 prediction으로 바뀌는 흐름을 봅니다 |
| 2장 | `labs/ch02_model_quality/02_train_evaluate_track_lab.ipynb` | 후보 모델을 반복 학습하고 평가 결과를 run 기록으로 남깁니다 |
| 2장 | `labs/ch02_model_quality/03_precision_recall.ipynb` | TP, FP, FN, Precision, Recall을 직접 계산합니다 |
| 2장 | `labs/ch02_model_quality/04_read_metric_record.ipynb` | 준비된 metric 기록 파일을 읽고 같은 기준으로 기록된 값을 확인합니다 |
| 3장 | `labs/ch03_serving/01_container_basics.ipynb` | image/container, Dockerfile, Compose 실행 조건을 확인합니다 |
| 3장 | `labs/ch03_serving/02_mlflow_model_uri.ipynb` | MLflow candidate URI와 평가 기록의 연결을 확인합니다 |
| 3장 | `labs/ch03_serving/03_fastapi_compose_serving.ipynb` | FastAPI + Compose 기반 요청/응답 계약을 확인합니다 |
| 3장 | `labs/ch03_serving/05_kubernetes_concepts.ipynb` | desired/live state, controller, scheduler, etcd 개념을 확인합니다 |
| 3장 | `labs/ch03_serving/06_kubernetes_mlflow_manifest.ipynb` | Kubernetes에 MLflow를 먼저 배포하는 manifest를 확인합니다 |
| 3장 | `labs/ch03_serving/07_argocd_kserve_manifest.ipynb` | Argo CD Application과 KServe manifest의 핵심 문자열을 확인합니다 |
| 3장 | `labs/ch03_serving/08_argocd_gitops_live_check.ipynb` | live sync와 KServe Ready 확인 조건을 정리합니다 |
| 4장 | `labs/ch04_observability/01_read_logs.ipynb` | JSONL 로그를 읽고 요청 단위 필드를 확인합니다 |
| 4장 | `labs/ch04_observability/02_compare_operational_numbers.ipynb` | baseline/current 로그의 오류율, latency, high_risk 비율을 비교합니다 |
| 5장 | `labs/ch05_qa_strategy/01_collect_release_evidence.ipynb` | 최종 확인에 필요한 report artifact 존재와 역할을 확인합니다 |
| 5장 | `labs/ch05_qa_strategy/02_read_release_report.ipynb` | `release_approval.md`의 실패 기준과 미확인 항목을 읽습니다 |

## 기존 Notebook 처리

기존 notebook은 삭제하지 않습니다. 다만 수업 기본 경로에서는 초급 notebook을 먼저 열고, 시간이 남거나 강사가 보충 설명이 필요할 때 기존 notebook을 reference로 사용합니다.

| 기존 유형 | 처리 |
| --- | --- |
| 긴 Pandas workbook | 강사용 상세 참고 또는 복습용 |
| MLflow/GX 전체 실행 notebook | Demo 또는 Appendix 성격으로 이동 |
| 3장/5장 통합 notebook | 초급 경로 후 종합 확인용으로 사용 |
