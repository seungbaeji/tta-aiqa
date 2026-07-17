# 1장 데이터 품질

## 1. 준비

### 1-1. 현재 데이터 작업 공간

`labs/README.md`의 공통 준비를 마친 뒤 다음 명령으로 현재 데이터 준비 상태가 최신인지
확인합니다.

```bash
uv run dvc status
```

공식 원본을 다시 내려받고 개별 기록 단위 특성 표를 재현해야 할 때만 실행합니다.

```bash
uv run python scripts/prepare_data.py
```

이 명령은 로컬 DVC 작업 공간과 Git이 추적하지 않는 실행 산출물을 갱신합니다. 확정된
과거 근거는 `docs/reference/evidence/`에서 읽기만 합니다.

### 1-2. 현재 평가 범위

이 실습의 개별 기록 단위 탐색은 4,000행 특성 표를 읽고, 모델 평가에 연결할 데이터
역할은 현재 분할 개정본에서 확인합니다.

```text
data/splits/physionet-2012/revisions/v2/split-manifest.csv
```

현재 역할별 건수는 `train 2,900 / valid 600 / test 400 / operational 100`입니다.
봉인된 `test` 400건과 정답이 없는 `operational` 100건은 서로 다른 역할을 가집니다.
이전 분할의 `2,400 / 600 / 600 / 400`을 현재 모델 지표의 범위로 사용하지 않습니다.

## 2. 수동 확인

### 2-1. Pandas 데이터 탐색

VS Code에서 `01_physionet_data_quality_eda.ipynb`를 열고 위에서 아래로 실행합니다.
노트북은 다음 데이터 품질 특성을 확인합니다.

- 레코드별 측정 행과 항목 수 차이
- 결측 표식인 `-1`
- 48시간 시각 범위
- 4,000개 정답 연결과 `high_risk` 554건
- 133개 특성과 변수별 결측 비율
- `train` 2,900, `valid` 600, 봉인된 `test` 400, 정답 없는 `operational` 100
- 라벨 결측, 허용값, 중복 식별자와 클래스별 표본 수
- 환자별 관측 행 수의 IQR 탐색 범위와 범위 밖 기록 수

수강생은 원본 관측값과 모델 입력 규약을 구분하고, 결측 표시와 학습 데이터에 맞춘
결측 처리의 역할을 나누어 봅니다. IQR 범위 밖 기록은 자동 삭제하지 않으며, 라벨 구조
점검은 정답 자체의 현실적 타당성을 증명하지 않습니다. 특성 선택과 모델 조정은 이
과정의 범위가 아닙니다.

## 3. 자동 검증

### 3-1. Great Expectations

데이터 탐색에서 확인한 구조 규칙을 원본 적재와 가공 데이터 준비 검사로 다시
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

공식 원본의 결측과 표식은 관측 근거이며 데이터셋을 자동으로 실패시키지 않습니다.
파일 수, 식별자, 시각, 가공 스키마, `target`과 결측 표시 규약 위반은 명령 실패로
보고됩니다. 이 명령은 DVC 데이터 게시 기준이 아닙니다. 또한 원본과 가공 구조를
검사할 뿐 봉인된 분할을 다시 평가하거나 Candidate B의 모델 승인을 판정하지 않습니다.
분할 이력은 `docs/reference/evidence/data-lineage/split-revision-v2.json`에서 읽기
전용으로 확인합니다.

## 4. 완료 기준

### 4-1. 확인 결과

- 노트북에서 원본 구조, 개별 기록 단위 행, 결측 비율 표를 확인합니다.
- 현재 분할 선언에서 `train`, `valid`, `test`, `operational`의 역할별 건수를 확인합니다.
- 라벨 구조, 클래스별 표본 수, IQR 범위 밖 관측 빈도를 확인하고 해석 범위를 구분합니다.
- GE 요약에서 원본 적재와 가공 데이터 준비가 모두 성공했는지 확인합니다.
- 어떤 값은 추가 조사 후보이고 어떤 값은 데이터 규약 실패인지 설명합니다.
- 보고서에는 데이터와 평가 범위, 한계를 남기고 검증 성공을 모델 승인이나 대상 환경
  배포 성공으로 쓰지 않습니다.
