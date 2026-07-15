# Model Trainer

## 1. 역할

### 1-1. Process boundary

`aiqa-model`의 development, diagnostics, bundle과 final confirmation use case를 `aiqa-qa` release policy, MLflow와 evidence adapter에 연결합니다. Feature와 model profile은 versioned YAML에서 읽습니다.

## 2. 실행

### 2-1. 수강생 경로

```bash
uv run python scripts/run_model.py status --revision v2
```

### 2-2. 새 Revision 강사용 재현 경로

```bash
uv run python scripts/run_model.py development --revision v2
uv run python scripts/run_model.py diagnostics --revision v2
uv run python scripts/run_model.py bootstrap --revision v2
```

이 명령 흐름은 새 revision을 만들 때만 사용합니다. `bootstrap`은 train/valid
bundle과 MLflow model run을 만든 뒤 `release-freeze.json`을 한 번 기록합니다.
freeze에는 clean Git commit, DVC/data-lineage, versioned configuration, exact
`test.csv`, 모든 model/metadata digest와 MLflow run ID가 들어갑니다.

freeze와 development/bootstrapping evidence를 검토해 commit한 뒤, source/config가
바뀌지 않은 clean worktree에서만 `final --sealed-test-token
CONFIRM-FROZEN-CANONICAL-TEST`을 실행합니다. final은 freeze를 수정하지 않고
`release-manifest.json`을 별도로 생성합니다.

V2는 이미 sealed test가 `evaluated_once`인 historical evidence입니다. V2에서는
`status`와 pre-built artifact만 확인하며 development, diagnostics, bootstrap, final을
다시 실행하지 않습니다.

## 3. 산출물

### 3-1. 경계

- Generated bundle와 MLflow: `artifacts/`
- Reviewable evidence: `docs/reference/evidence/model/revisions/<revision>`
- Pre-test freeze: `release-freeze.json`
- Post-test release decision: `release-manifest.json`
