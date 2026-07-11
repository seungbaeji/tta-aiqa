# Model Trainer

## 1. 역할

### 1-1. Process boundary

`aiqa-model`의 development, diagnostics, bundle과 final confirmation use case를 `aiqa-qa` release policy, MLflow와 evidence adapter에 연결합니다. Feature와 model profile은 versioned YAML에서 읽습니다.

## 2. 실행

### 2-1. 수강생 경로

```bash
uv run python scripts/run_model.py status --revision v2
```

### 2-2. 강사용 재현 경로

```bash
uv run python scripts/run_model.py development --revision v2
uv run python scripts/run_model.py diagnostics --revision v2
uv run python scripts/run_model.py bootstrap --revision v2
```

Sealed test `final`은 새 revision의 freeze가 끝난 뒤 한 번만 수행합니다. 기존 V2 canonical evidence를 덮어쓰지 않습니다.

## 3. 산출물

### 3-1. 경계

- Generated bundle와 MLflow: `artifacts/`
- Reviewable evidence: `reference/evidence/model/revisions/<revision>`
