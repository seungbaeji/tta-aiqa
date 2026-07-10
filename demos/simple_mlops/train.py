"""Train a risk model and publish the latest model artifact.

이 파일은 세 가지를 한 번에 보여줍니다.
1. CSV 데이터로 모델 학습
2. MLflow에 parameter/metric/model 기록
3. FastAPI가 읽을 최신 model file 저장
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# app.py와 같은 feature 목록을 사용해야 학습/서빙 입력이 어긋나지 않습니다.
FEATURES = [
    "heart_rate",
    "respiratory_rate",
    "body_temperature",
    "oxygen_saturation",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
]
LABEL = "label"
POSITIVE_LABEL = "high_risk"


def parse_args() -> argparse.Namespace:
    # Docker Compose에서는 대부분 기본값과 환경 변수를 그대로 사용합니다.
    # 로컬에서 실험할 때만 CLI 인자로 경로를 바꾸면 됩니다.
    parser = argparse.ArgumentParser(description="Train and log a risk model.")
    parser.add_argument("--train-path", default="/app/data/vital_signs_train.csv")
    parser.add_argument("--test-path", default="/app/data/vital_signs_test.csv")
    parser.add_argument(
        "--model-path",
        default=os.getenv("MODEL_PATH", "/app/models/latest_model.joblib"),
    )
    parser.add_argument(
        "--metadata-path",
        default=os.getenv("METADATA_PATH", "/app/models/latest_metadata.json"),
    )
    parser.add_argument(
        "--tracking-uri",
        default=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"),
    )
    parser.add_argument("--experiment", default="simple-aiqa-risk-classifier")
    parser.add_argument("--repeat", type=int, default=1, help="0 means forever")
    parser.add_argument("--interval", type=float, default=60.0)
    return parser.parse_args()


def wait_for_mlflow(tracking_uri: str, timeout_seconds: float = 60.0) -> None:
    """Wait until the MLflow server is ready.

    docker compose가 여러 container를 동시에 띄우기 때문에 trainer가 MLflow보다
    먼저 시작될 수 있습니다. 그 경우를 막기 위한 작은 준비 확인입니다.
    """

    if urlparse(tracking_uri).scheme not in {"http", "https"}:
        return

    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with urllib.request.urlopen(tracking_uri, timeout=2.0) as response:
                if response.status < 500:
                    return
        except Exception:
            pass

        if time.monotonic() >= deadline:
            raise TimeoutError(f"MLflow is not ready: {tracking_uri}")
        time.sleep(2.0)


def model_destination_kwargs(name: str) -> dict[str, str]:
    # MLflow version에 따라 log_model 인자 이름이 name 또는 artifact_path일 수 있습니다.
    parameters = inspect.signature(mlflow.sklearn.log_model).parameters
    if "name" in parameters:
        return {"name": name}
    return {"artifact_path": name}


def load_xy(path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load features and convert the text label to a binary target."""

    dataframe = pd.read_csv(path)
    return dataframe.loc[:, FEATURES], (dataframe[LABEL] == POSITIVE_LABEL).astype(int)


def train_once(args: argparse.Namespace, run_index: int) -> dict[str, object]:
    """Train one model, log it to MLflow, and save it for the API."""

    # loop 학습 때마다 seed/max_depth를 조금 바꿔
    # MLflow run 차이를 눈으로 볼 수 있게 합니다.
    seed = int(time.time()) % 1_000_000 + run_index
    max_depth = 4 + (seed % 5)
    n_estimators = 80

    train_x, train_y = load_xy(args.train_path)
    test_x, test_y = load_xy(args.test_path)

    # Pipeline으로 preprocessing과 model을 묶으면
    # serving에서도 같은 변환이 자동 적용됩니다.
    model = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    min_samples_leaf=5,
                    random_state=seed,
                    n_jobs=-1,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    model.fit(train_x, train_y)

    # threshold는 metadata에도 저장해 API가 같은 기준으로 label을 결정하게 합니다.
    probabilities = model.predict_proba(test_x)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = {
        "accuracy": accuracy_score(test_y, predictions),
        "precision": precision_score(test_y, predictions, zero_division=0),
        "recall": recall_score(test_y, predictions, zero_division=0),
        "f1": f1_score(test_y, predictions, zero_division=0),
    }
    params = {
        "features": ",".join(FEATURES),
        "label": LABEL,
        "positive_label": POSITIVE_LABEL,
        "threshold": 0.5,
        "model_type": "RandomForestClassifier",
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "seed": seed,
    }

    now = datetime.now(UTC).isoformat()
    with mlflow.start_run(run_name=f"train-{now}") as run:
        # MLflow에는 재현과 비교에 필요한 값들을 나누어 기록합니다.
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            sk_model=model,
            input_example=test_x.head(3),
            **model_destination_kwargs("model"),
        )
        metadata = {
            "trained_at": now,
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "tracking_uri": args.tracking_uri,
            "features": FEATURES,
            "threshold": 0.5,
            "metrics": metrics,
            "params": params,
        }

        # API container는 이 두 파일만 읽으면 최신 모델과 그 metadata를 알 수 있습니다.
        model_path = Path(args.model_path)
        metadata_path = Path(args.metadata_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "metadata": metadata}, model_path)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        mlflow.log_artifact(str(metadata_path))

    # compose logs에서 바로 확인하기 좋게 한 줄 JSON으로 출력합니다.
    print(
        json.dumps(
            {
                "model_path": args.model_path,
                "metadata_path": args.metadata_path,
                "run_id": metadata["run_id"],
                "metrics": metrics,
            },
            ensure_ascii=False,
        )
    )
    return metadata


def main() -> None:
    args = parse_args()
    wait_for_mlflow(args.tracking_uri)
    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment)

    # --repeat 0은 무한 loop입니다. trainer-loop container가 이 모드를 사용합니다.
    run_index = 0
    while args.repeat == 0 or run_index < args.repeat:
        run_index += 1
        train_once(args, run_index)
        if args.repeat == 0 or run_index < args.repeat:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
