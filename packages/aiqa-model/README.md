# aiqa-model

## 1. 책임

### 1-1. Model lifecycle

Model profile catalog, evaluation metric, profile selection, sealed-test confirmation과 benchmark result를 immutable domain value로 관리합니다. `valid` evidence는 `train`/`valid` 역할만 사용하고, final evidence는 frozen model bundle을 다시 학습하지 않은 채 sealed `test`에 한 번만 평가합니다.

### 1-2. Application and ports

Application은 함수형 use case로 `develop_models`, `diagnose_features`, `fit_model_bundles`, `confirm_frozen_models`를 제공한다. 각각 development evaluation, feature diagnostics, frozen fitting, frozen-model evaluation이라는 좁은 port만 받으며, 선택한 profile 집합과 반환 evidence가 일치하는지 검증한다.

### 1-3. Adapters

`adapters.sklearn`은 CSV role reader, pipeline construction, evaluation, diagnostics, fitting을 분리한다. `adapters.config`과 `adapters.evidence`는 Pydantic DTO로 YAML/JSON 경계를 검증하고, `adapters.bundles`와 `adapters.mlflow`는 joblib, checksum, MLflow 같은 기술적 I/O를 소유한다.
