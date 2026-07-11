# 2장 모델 품질

## 1. 목표

### 1-1. 증거 비교

Baseline, Candidate A와 Candidate B를 같은 test 기준으로 비교하고 단일 metric이 아니라 release guardrail 전체로 판단합니다. 모델 개발과 tuning 과정은 이 실습 범위가 아닙니다.

## 2. 실행

### 2-1. Canonical 상태

```bash
uv run python scripts/run_model.py status --revision v2
```

Candidate A `HOLD`, Candidate B `APPROVE`가 출력되어야 합니다.

### 2-2. Notebook

VS Code에서 `01_compare_model_evidence.ipynb`를 열어 위에서 아래로 실행합니다. PR-AUC, Precision, Recall, FN과 bootstrap lower bound를 함께 비교합니다.

### 2-3. MLflow

```bash
uv run mlflow server \
  --backend-store-uri sqlite:///artifacts/mlflow/mlflow.db \
  --host 127.0.0.1 \
  --port 5000
```

강사가 제공한 MLflow URL을 사용하는 경우 로컬 server를 시작하지 않습니다. 세 profile의 parameter, validation metric과 dataset lineage가 기록됐는지 확인합니다.

## 3. 완료 기준

### 3-1. 판단

- Candidate A가 어떤 guardrail 때문에 보류됐는지 설명할 수 있습니다.
- Candidate B가 Recall과 FN을 개선하면서 Precision floor를 지켰는지 확인합니다.
- sealed test 결과를 보고 feature나 threshold를 다시 조정하지 않습니다.
