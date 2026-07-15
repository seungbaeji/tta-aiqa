# Chapter 1: Data Quality

## 1. 준비

### 1-1. Current data workspace

`labs/README.md`의 공통 setup을 완료한 뒤 다음 명령으로 current data pipeline이
up-to-date인지 확인합니다.

```bash
uv run dvc status
```

공식 원본을 다시 내려받고 patient-level data를 재현해야 할 때만 실행합니다.

```bash
uv run python scripts/prepare_data.py
```

이 명령은 local DVC workspace와 ignored runtime artifact를 갱신합니다. sealed V2
evidence는 `docs/reference/evidence/`에서 읽기만 합니다.

### 1-2. V2 evaluation scope

이 Lab의 patient-level EDA는 4,000행 feature table을 읽고, model evidence에 연결할
role은 반드시 V2 split revision에서 읽습니다.

```text
data/splits/physionet-2012/revisions/v2/split-manifest.csv
```

V2 role은 `train 2,900 / valid 600 / test 400 / operational 100`입니다. 새 sealed
test 400건과 target 없는 operational 100건은 V1 parent split과 다른 lifecycle 역할을
가집니다. parent split의 `2,400 / 600 / 600 / 400` count를 V2 model metric의 범위로
쓰지 않습니다.

## 2. 수동 확인

### 2-1. Pandas EDA

VS Code에서 `01_physionet_data_quality_eda.ipynb`를 열고 위에서 아래로 실행합니다.
Notebook은 다음 실제 품질 특성을 확인합니다.

- 환자별 측정 행과 parameter 수 차이
- `-1` missing sentinel
- 48시간 timestamp 범위
- 4,000개 outcome join과 사망 554건
- 133개 available feature와 변수별 missing 비율
- V2 train 2,900, valid 600, sealed test 400, target-free operational 100 role
  count

QA 담당자는 raw observation과 model-ready contract를 구분하고, 개발자와 ML
Engineer는 missing indicator와 train-fitted imputation의 책임을 구분합니다.
Feature selection과 모델 튜닝은 이 과정의 범위가 아닙니다.

## 3. 자동 검증

### 3-1. Great Expectations

EDA에서 확인한 구조 규칙을 raw ingestion과 processed readiness checkpoint로 다시
실행합니다.

```bash
uv run python scripts/validate_data.py
```

생성 결과:

```text
artifacts/data-quality/great-expectations/validation-summary.json
artifacts/data-quality/great-expectations/raw/gx/uncommitted/data_docs/
artifacts/data-quality/great-expectations/processed/gx/uncommitted/data_docs/
```

공식 원본의 missing과 sentinel은 관찰 evidence이며 dataset을 실패시키지 않습니다.
파일 수, identifier, timestamp, processed schema, target과 missing indicator 계약
위반은 command 실패로 보고됩니다. 이 command는 DVC dataset publish gate가 아닙니다.
또한 이 checkpoint는 raw/processed structure를 검사하며 V2 sealed split을 다시
평가하거나 Candidate B의 model approval을 판정하지 않습니다. V2 split lifecycle은
`docs/reference/evidence/data-lineage/split-revision-v2.json`에서 read-only로
확인합니다.

## 4. 완료 기준

### 4-1. Evidence

- EDA notebook에서 raw profile, patient-level rows, missing-rate table을 확인합니다.
- V2 split manifest에서 train/valid/test/operational role count를 확인합니다.
- GE summary에서 raw ingestion과 processed readiness가 모두 success인지 확인합니다.
- 어떤 문제는 관찰 evidence이고 어떤 문제는 contract failure인지 설명합니다.
- report에는 data/evaluation scope와 limitation을 남기고, validation success를 model
  approval 또는 target deployment success로 쓰지 않습니다.
