# Chapter 1: Data Quality

## 1. 준비

### 1-1. 데이터 재현

Repository root에서 공식 원본의 checksum을 확인하고 patient-level 데이터를 생성합니다.

```bash
uv run python scripts/prepare_data.py
```

## 2. 수동 확인

### 2-1. Pandas EDA

VS Code에서 `01_physionet_data_quality_eda.ipynb`를 열고 위에서 아래로 실행합니다. Notebook은 다음 실제 품질 특성을 확인합니다.

- 환자별 측정 행과 parameter 수 차이
- `-1` missing sentinel
- 48시간 timestamp 범위
- 4,000개 outcome join과 사망 554건
- 133개 available feature와 변수별 missing 비율

Feature selection과 모델 튜닝은 이 과정의 범위가 아닙니다.

## 3. 자동 검증

### 3-1. Great Expectations

EDA에서 확인한 구조 규칙을 raw ingestion과 processed readiness checkpoint로 다시 실행합니다.

```bash
uv run python scripts/validate_data.py
```

생성 결과:

```text
artifacts/data-quality/great-expectations/validation-summary.json
artifacts/data-quality/great-expectations/raw/gx/uncommitted/data_docs/
artifacts/data-quality/great-expectations/processed/gx/uncommitted/data_docs/
```

공식 원본의 missing과 sentinel은 관찰 evidence이며 dataset을 실패시키지 않습니다. 파일 수, identifier, timestamp, processed schema, target과 missing indicator 계약 위반은 command 실패로 보고됩니다. 이 command는 DVC dataset publish gate가 아닙니다.
