# Data

## 1. V2 기준 데이터

### 1-1. 공식 원본

V2는 PhysioNet/Computing in Cardiology Challenge 2012 version 1.0.0의 Set A를 사용합니다.

```text
data/raw/physionet-2012/
├── set-a.zip
├── Outcomes-a.txt
├── LICENSE.txt
└── source-manifest.yaml
```

Archive와 outcome은 공식 배포 파일 그대로 보존합니다. 출처, 라이선스, 인용문, 파일 크기와 SHA-256은 `source-manifest.yaml`이 단일 기준입니다. Git은 manifest와 license notice만 관리하며 archive와 outcome은 준비 명령이 공식 URL에서 내려받습니다.

### 1-2. 생성 데이터

압축 해제 결과와 patient-level 파생 데이터는 원본에서 재현하며 Git에 포함하지 않습니다.

```text
data/interim/physionet-2012/set-a/
data/processed/
data/splits/
data/traffic/
```

운영체제에 관계없이 다음 명령으로 공식 원본을 내려받아 checksum을 검증하고 DVC pipeline을 재현합니다.

```bash
uv run python scripts/prepare_data.py
```

## 2. AS-IS 호환 데이터

### 2-1. 제거 예정 파일

과거 Kaggle 원본, `vital_signs*.csv`, request CSV와 JSONL 파일은 `legacy/`에만 보존합니다. V2 app은 이 파일들을 import하거나 입력으로 사용하지 않습니다.
