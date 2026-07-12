## 1. 검증 기준

### 1-1. 목적

이 문서는 V2 구현에서 실제로 실행한 검증과 외부 환경이 필요해 아직 실행하지 않은 검증을 구분한다. Manifest inspection, local runtime, target k3s sync와 Grafana Cloud ingestion을 같은 증거로 표현하지 않는다.

## 2. 완료한 자동 검증

### 2-1. Repository

- `uv lock --check`
- `ruff check apps packages scripts tests`
- `pytest`: 176 passed
- `dvc status`: active data-pipeline/package code dependency 변경을 감지했다. Historical V2 evidence를 보존하기 위해 이 working tree에서 `dvc repro`는 실행하지 않았다.
- 학생용 ch01~ch05 Notebook top-to-bottom 실행
- baseline, baseline-observed, Candidate B와 rollback Kustomize render
- Compose base와 Grafana Cloud override render
- Compose/Kubernetes Alloy config를 `grafana/alloy:v1.16.1 validate`로 검사

### 2-2. Curriculum

- `ttamlops-2607` package tests: 85 passed
- `mkdocs build --strict`
- public site에서 V1 JupyterLite build와 Kaggle/legacy Lab 경로 제외
- curriculum canonical SHA와 sibling evidence 일치

## 3. 완료한 Local Runtime 검증

### 3-1. Compose

- Baseline Risk API readiness와 `/v1/model`
- 독립 Traffic Generator baseline 요청 5건, HTTP 200
- `/metrics`의 baseline profile/version/scenario label

### 3-2. KServe adapter

- Custom KServe predictor와 Risk API를 별도 process로 실행
- KServe readiness와 model identity 검증
- KServe backend를 통한 baseline traffic 3건, HTTP 200
- Local OrbStack 8080 충돌을 확인하고 configurable predictor port로 우회

### 3-3. Artifact

- Existing serialized baseline/Candidate A/Candidate B bundle이 frozen canonical metric과 완전히 일치
- Model과 external metadata hash를 release manifest와 publish gate에서 검증
- Candidate B immutable publish 경로 생성과 metadata 검증

### 3-4. Provenance Scope and Remaining Work

현재 V2 evidence와 publish gate는 serialized model과 external metadata의 hash를
검증한다. 그러나 pre-test freeze에서 exact `test.csv`와 모든 bundle digest를 먼저
동결하고, KServe startup에서 expected model digest를 검증하며, Kubernetes image를
OCI digest로 pin하는 target contract는 아직 구현 완료가 아니다. 이 구분과 도구별
책임은 [ADR 0006](adr/0006-layered-artifact-identity-and-release-provenance.md)에
정의한다.

## 4. 외부 환경 Pending

### 4-1. Target k3s와 Argo CD

현재 kubectl context는 수업 VM이 아닌 `oracle/k3s`이므로 resource를 적용하지 않았다. Target VM에서 static `/mnt/course-models` PV, baseline sync, Candidate B sync와 rollback health를 확인해야 한다.

### 4-2. Grafana Cloud

개인 `.env.grafanacloud`와 Alloy Secret이 없어 live ingestion과 dashboard import를 실행하지 않았다. 개인 stack에서 baseline telemetry, Candidate B telemetry 누적과 dashboard idempotency를 확인해야 한다.

### 4-3. Clean clone

현재 active 구조 refactor와 검증 변경은 아직 working tree에 있다. 해당 변경을 commit한 뒤 빈 clone에서 `uv sync --all-packages --group notebook`과 `uv run python scripts/setup_course.py --data-only`를 실행해야 한다.

### 4-4. Container image

Kubernetes manifests의 `ghcr.io/seungbaeji/tta-aiqa-risk-api:v2`와 `ghcr.io/seungbaeji/tta-aiqa-kserve-predictor:v2`는 아직 immutable digest로 고정되지 않았다. Release image publish 후 digest pinning과 target architecture pull을 확인해야 한다.
