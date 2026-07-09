# Chapter 2 Evaluation Record Demo

이 Demo는 2-4 scikit-learn 모델 평가 실습에서 만든 평가 기록을 JSON과 선택적 MLflow tracking으로 확인하는 흐름을 보여줍니다. 수업의 필수 근거는 `artifacts/experiments/chapter_02/model_test_eval.json`이며, MLflow는 같은 기록을 추적 도구로 확인하는 선택 경로입니다.

MLflow를 켠 환경에서는 단순 metric 기록보다 한 단계 더 남깁니다.

| MLflow 항목 | 이번 Demo에서 남기는 내용 |
| --- | --- |
| params | dataset name/version/digest, model name/version, feature columns, threshold |
| metrics | accuracy, precision, recall, F1, AUROC, PR-AUC, FP, FN |
| dataset input | `vital_signs_test.csv`를 `mlflow.data.from_pandas`와 `mlflow.log_input`으로 연결 |
| tags | chapter, QA stage, dataset/model version, run purpose |
| artifacts | JSON 평가 기록과 원본 pickle model |
| model | sklearn model, signature, input example, model metadata |

여기서 dataset versioning은 “MLflow가 데이터 파일을 Git처럼 관리한다”는 뜻이 아니라, run이 사용한 dataset의 version label, source path, content digest를 추적한다는 뜻입니다. 실제 데이터 저장/승인 정책은 Git, DVC, lakeFS, object storage 같은 별도 저장소 정책과 함께 두고, MLflow는 “어떤 run이 어떤 dataset fingerprint를 사용했는가”를 감사 근거로 남기는 역할에 가깝습니다.

2-4 Lab에서 평가 기록을 생성할 때는 다음 명령을 사용합니다.

```bash
uv run --group lab python labs/ch02_model_quality/evaluate_and_record.py
```

MLflow까지 함께 확인하려면 다음처럼 실행합니다.

```bash
uv run --group demo python demos/ch02_mlflow/run_demo.py
```

MLflow가 설치되어 있으면 `artifacts/mlflow.db`에 local tracking 결과를 남깁니다. 설치되어 있지 않아도 `model_test_eval.json`으로 dataset, dataset digest, feature, 라벨 기준, model version, threshold, metric을 확인할 수 있습니다.

### Docker MLflow 서버 연결(검증용)

실무형 실행이 아니어도 아래처럼 MLflow 서버 컨테이너를 띄워 기존 실습이 정상 연결되는지 확인할 수 있습니다.

```bash
docker run -d --name ai-mlflow \
  -p 5001:5000 \
  -v "$(pwd)/artifacts/mlflow:/mlflow" \
  ghcr.io/mlflow/mlflow:latest \
  mlflow server \
    --backend-store-uri sqlite:////mlflow/mlflow.db \
    --default-artifact-root /mlflow/artifacts \
    --host 0.0.0.0 \
    --port 5000
```

```bash
MLFLOW_TRACKING_URI=http://127.0.0.1:5001 \
uv run --group demo python demos/ch02_mlflow/run_demo.py
```

성공하면 출력에 `mlflow tracking` 항목으로 `http://127.0.0.1:5001`이 표시됩니다. UI에서는 experiment `ai-quality-chapter-02`의 `model_test_eval` run을 열어 `Parameters`, `Metrics`, `Inputs`, `Tags`, `Artifacts`, `Models`를 확인합니다.

원샷으로 확인하려면 아래 스크립트를 실행하세요.

```bash
bash demos/ch02_mlflow/run_with_docker_mlflow.sh
```

포트 충돌이 있는 환경이면 `MLFLOW_PORT`로 바꿔 실행하세요.

```bash
MLFLOW_PORT=5001 bash demos/ch02_mlflow/run_with_docker_mlflow.sh
```
