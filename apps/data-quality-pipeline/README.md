# Data Quality Pipeline

## 1. 역할

### 1-1. Process boundary

PhysioNet 원본 검증, 압축 해제, patient-level 집계, deterministic split과 Great Expectations validation을 조립합니다. 데이터 계산 규칙은 `aiqa-data`, GE와 filesystem 연동은 이 app의 adapter가 담당합니다.

## 2. 실행

### 2-1. 전체 데이터 준비

```bash
uv run python scripts/prepare_data.py
```

### 2-2. GE 검증

```bash
uv run python scripts/validate_data.py
```

## 3. 산출물

### 3-1. 경계

- DVC output: `data/interim`, `data/processed`, `data/splits`
- Runtime evidence: `artifacts/data-quality`
- Canonical lineage: `docs/reference/evidence/data-lineage`
