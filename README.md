# TTA AIQA Monorepo

Simple MLOps demo를 중심으로 다시 정리한 작업 공간입니다. 이전 course/lab 자료는 삭제하지 않고 `legacy/` 아래로 이동했습니다.

## 1. 구조

### 1-1. 현재 작업 대상

```text
apps/simple_mlops/   MLflow, FastAPI, Docker Compose 기반 MLOps demo
data/                원본 CSV와 로컬에서 재생성되는 파생 데이터
docs/                새 모노레포 설계와 작업 계획
packages/            재사용 가능한 data/model/observability/core package
scripts/             repo 공통 유틸리티
legacy/              이전 labs, packages, artifacts, docs, gitops, demos 보관
```

### 1-2. Package 역할

```text
packages/aiqa-core/            feature, label, threshold, path helper
packages/aiqa-data/            원본 CSV 표준화와 파생 데이터 생성
packages/aiqa-model/           sklearn 학습, 평가, model 저장, MLflow logging
packages/aiqa-observability/   prediction event, Prometheus metrics, OTLP trace
```

`apps/simple_mlops`는 FastAPI route, CLI argument parsing, Docker/Compose, runtime 설정만 담당합니다.

## 2. 준비

### 2-1. uv 설치

`uv`가 없다면 먼저 설치합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell에서는 다음 명령을 사용합니다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

다운로드와 추가 설치 옵션은 uv 공식 문서의 설치 페이지에서 확인합니다.

```text
https://docs.astral.sh/uv/getting-started/installation/
```

### 2-2. 의존성 설치

의존성을 설치합니다.

```bash
uv sync
```

## 3. 데이터 생성

### 3-1. 원본 데이터에서 파생 데이터 만들기

Git에는 원본 CSV인 `data/human_vital_signs_dataset_2024.csv`만 유지합니다. demo가 사용하는 학습/서빙용 파생 데이터는 다음 명령으로 생성합니다.

```bash
uv run python scripts/prepare_data.py
```

이 wrapper는 내부적으로 `packages/aiqa-data`의 `prepare_datasets()`를 호출합니다.

### 3-2. 생성되는 주요 파일

생성되는 주요 파일은 다음과 같습니다.

```text
data/vital_signs_train.csv
data/vital_signs_test.csv
data/serving_requests.csv
data/serving_requests_current.csv
data/operational_current_events.jsonl
```

데이터 split과 샘플링은 `random_state=42`로 고정되어 있습니다.

## 4. Simple MLOps 실행

### 4-1. 전체 demo 실행

```bash
cd apps/simple_mlops
docker compose --profile continuous build
docker compose --profile continuous up -d
```

### 4-2. 작은 VM에서 한 번씩 실행

작은 VM에서는 한 번만 실행하는 흐름을 먼저 확인합니다.

```bash
cd apps/simple_mlops
docker compose up -d mlflow
docker compose --profile train run --rm trainer
docker compose up -d api
docker compose --profile traffic run --rm traffic
```

### 4-3. 확인 URL

확인 URL:

```text
MLflow          http://localhost:5002
FastAPI docs    http://localhost:8000/docs
API health      http://localhost:8000/health
Metrics         http://localhost:8000/metrics
```

자세한 내용은 `apps/simple_mlops/README.md`를 봅니다.

## 5. Legacy

### 5-1. 이전 자료 위치

이전 자료는 `legacy/`에 남겨 두었습니다.

```text
legacy/README.course.md
legacy/labs/
legacy/packages/
legacy/artifacts/
legacy/demos/
legacy/gitops/
```

새 작업에서는 `apps/simple_mlops`를 기준으로 필요한 코드만 다시 끌어올립니다.

## 6. V2 TO-BE 계획

### 6-1. 기획 문서

현재 구현을 네 개 app과 여섯 개 bounded-context package로 재구성하고 DVC, Great Expectations, 실제 baseline/candidate model, GitOps 배포, 운영 관측과 release decision을 연결하는 V2 계획은 [docs/v2-to-be-plan.md](docs/v2-to-be-plan.md)에 정리했습니다.
