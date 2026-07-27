# V2 구현 검증 상태

> 이 문서는 강사·플랫폼 담당자를 위한 개발·운영 검증 기록입니다. 수강생 실습
> 절차는 `labs/`의 장별 README를 따릅니다.

## 1. 검증 기준

### 1-1. 목적

이 문서는 V2 구현에서 실제로 실행한 검증과 외부 환경이 필요해 아직 실행하지 않은 검증을 구분한다. Manifest inspection, local runtime, target k3s sync와 Grafana Cloud ingestion을 같은 증거로 표현하지 않는다.

## 2. 완료한 자동 검증

### 2-1. Repository

- `uv lock --check`
- `ruff check apps packages scripts tests`
- 전체 `pytest`: 345 passed
- trace topology와 propagation contract: `traffic.generate` -> Traffic CLIENT -> Risk API SERVER -> `risk.predict` parent-child, Risk API KServe CLIENT context 전달, probe/scrape trace 제외
- `dvc repro` 후 `dvc status`: `Data and pipelines are up to date.`
- 학생용 ch01~ch05 Notebook top-to-bottom 실행
- baseline, baseline-observed, Candidate B와 rollback Kustomize render
- Compose base와 Grafana Cloud override render
- Compose/Kubernetes Alloy config를 pinned Alloy digest로 검사
- 빈 clone에서 `uv sync --all-packages --group notebook`,
  `uv run python scripts/setup_course.py --data-only`, notebook suite와 clean
  `git status`를 확인

### 2-2. Curriculum

- `ttamlops-2607` package tests: 124 passed
- V1·V2 `mkdocs build --strict`
- public site에서 V1 JupyterLite build와 Kaggle/legacy Lab 경로 제외
- curriculum canonical SHA와 sibling evidence 일치

## 3. 완료한 Local Runtime 검증

### 3-1. Compose

- 현재 Compose build 후 baseline Risk API readiness와 `/v1/model`
- 독립 Traffic Generator baseline 요청 5건, HTTP 200
- invalid traffic 3건, HTTP 422
- `/metrics`의 baseline profile/version/scenario label

### 3-2. KServe adapter

- Custom KServe predictor와 Risk API를 별도 process로 실행
- KServe readiness와 model identity 검증
- KServe backend를 통한 baseline traffic 3건, HTTP 200
- Local OrbStack 8080 충돌을 확인하고 configurable predictor port로 우회
- Predictor startup이 ConfigMap의 expected model SHA-256과 mounted bundle이 다르면
  실패하는 integration test

### 3-3. Artifact

- Existing serialized baseline/Candidate A/Candidate B bundle이 frozen canonical metric과 완전히 일치
- Model과 external metadata hash를 release manifest와 publish gate에서 검증
- Candidate B immutable publish 경로 생성과 metadata 검증
- Risk API와 KServe predictor를 source commit
  `8e5c14dd773dbfcbd0896a6edbd522e9a035abf6` label로 GHCR에
  `linux/amd64`/`linux/arm64` OCI index로 게시하고 digest를 배포 선언에 고정
- [V2 런타임 이미지 근거](reference/evidence/deployment/runtime-images-v2.json)에
  source commit, OCI index digest, 플랫폼과 로컬 smoke 결과를 기록하고 배포
  계약 테스트에서 manifest와 대조
- 로컬 `linux/arm64`에서 고정 digest를 다시 pull한 뒤 predictor readiness,
  Risk API readiness와 `/v1/model`, Risk API→predictor baseline HTTP 200을 확인

### 3-4. Provenance Scope and Remaining Work

새 revision의 release freeze는 exact sealed `test.csv`와 model/metadata digest를
test 전에 동결한다. V2 historical revision은 migration 전 원본 frozen DVC lock blob을
repo에서 복원할 수 없으므로, `release-manifest.json`의 `historical_reconciliation`에
검증 범위를 명시한다. KServe startup digest gate와 OCI digest pinning은 구현됐으며
도구별 책임은 [ADR 0006](adr/0006-layered-artifact-identity-and-release-provenance.md)에
정의한다.

## 4. 외부 환경 Pending

### 4-1. Target k3s와 Argo CD

현재 설정된 kubectl context는 수업 VM이 아닌 `oracle/k3s`이며 과정용
`tta-aiqa` namespace와 런타임이 없다. 이 클러스터에는 resource를 적용하지
않았다. Target VM context를 제공받으면 static `/mnt/course-models` PV,
`ghcr-pull` registry Secret, baseline sync, Candidate B sync와 rollback health를
강사·플랫폼 담당자가 확인해야 한다. 완료 근거는 대상 node의 고정 digest pull,
baseline·Candidate B·rollback의 모델 정보와 health, 같은 모델·시간대의 운영
신호다. 각 동기화 단계에서는 `scripts/verify_target_release.py`가 context를
고정한 읽기 전용 검사로 desired image, 실제 Pod의 platform manifest digest,
모델 해시·경로, API 모델 정보와 정상 요청을 JSON 보고서에 남긴다. 이 보고서는
Grafana 확인을 대신하지 않으며 live telemetry는 별도 근거가 있을 때만 완료로
바꾼다.

### 4-2. Grafana Cloud

개인 `.env.grafanacloud`와 Alloy Secret이 없어 live ingestion과 dashboard import를 실행하지 않았다. 개인 stack에서 baseline telemetry, Candidate B telemetry 누적과 dashboard idempotency를 확인해야 한다.

### 4-3. Target image pull

GHCR OCI index에는 `linux/amd64`와 `linux/arm64` manifest가 모두 존재하며 로컬
`linux/arm64` pull과 source revision label을 확인했다. 실제 course VM node가
private package를 `ghcr-pull` Secret으로 pull하는지와 Argo CD rollout에서
digest가 유지되는지는 target k3s에서 확인해야 한다.
