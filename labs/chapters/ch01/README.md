# 1장 데이터 품질

이 장은 데이터가 어떻게 나뉘었는지, 원본 품질이 어떤지, 자동 검증이 무엇을
말하는지 확인합니다. 첫 사건인 [배포된 baseline 관찰](../../README.md#배포된-baseline-관찰)은
[`labs/README.md`](../../README.md)에서 먼저 닫습니다.

## 1. 본편 실습

노트북과 검증 명령은 원본 측정에서 기록 단위 분할과 자동 검증 결과로
이어집니다. 공식 평가 자료는 학습에 쓰지 않습니다.

### 1-1. train, valid, sealed test, operational의 역할을 누수 없이 구분한다

지금 데이터가 최신 선언과 같은지 본 뒤, 역할 표를 읽습니다. 현재 역할은
`train 2,900 / valid 600 / test 400 / operational 100`입니다. 실행 전에 개발 평가,
공식 평가, 정답 없는 운영 표본의 역할을 예측한 뒤 표와 대조합니다. 이전 분할
`2,400 / 600 / 600 / 400`을 현재 판단에 섞지 않습니다.

```bash
uv run dvc status
```

역할 표는 `data/splits-v2/split-manifest.csv`입니다.

### 1-2. PhysioNet raw measurement의 결측, 범위, join을 데이터 품질 근거로 해석한다

`01_physionet_data_quality_eda.ipynb`를 위에서 아래로 실행해 기록별 측정 행,
`-1` 결측 표식, 48시간 관측 창, 4,000개 결과 연결, 133개 특성과 결측률을 봅니다.
계약 YAML은 `yaml.safe_load`로 열고, 원본 txt는 `pd.read_csv`로 읽습니다.
측정 구조 요약과 원본 변수별 표는 4GiB VM 메모리를 위해 고른 표본 파일만 읽습니다.
4,000행 특성 표는 가공 CSV입니다.
IQR 범위 밖 기록을 자동 삭제하지 않고, 관측 근거와 규약 위반을 구분해 판단
기록의 데이터 품질 칸에 적습니다. 특성 선택과 모델 조정은 하지 않습니다.

공식 원본과 개별 기록 단위 표를 다시 만들어야 할 때만 다음 명령을 실행합니다.

```bash
uv run python labs/run/prepare_data.py
```

### 1-3. GE summary가 데이터 품질 관찰을 재현 가능한 evidence로 닫는지 판단한다

노트북에서 본 원본/가공 규칙을 다음 명령으로 실행합니다.

```bash
uv run python labs/run/validate_data.py
```

실행 후 `artifacts/data-quality/great-expectations/validation-summary.json`과
Data Docs가 생성됩니다. 이 결과는 데이터 품질 근거입니다. 게시 차단, 모델
승인, 대상 환경 통과를 대신하지 않습니다. 실행하지 못하면 `offline` 또는
`BLOCKED`로 적고 준비된 읽기 전용 근거를 사용합니다.

실행 결과 또는 준비된 근거를 먼저 읽은 뒤, 학생이 편집할 파일
`labs/exercises/ge_summary.py`와 테스트
`labs/exercises/tests/test_ge_summary.py`를 확인합니다. 이 연습의 함수는
검증을 다시 실행하거나 파일을 쓰지 않고, 요약이 무엇을 말하는지 해석합니다.

`success=true`여도 이 근거가 게시 결정을 담당하지 않을 수 있습니다. 시작
상태를 확인합니다.

```bash
uv run pytest -q labs/exercises/tests/test_ge_summary.py -m regression
```

regression 표시는 12개가 통과해야 합니다. 이어서 current goal을 실행하면
시작 상태의 두 `AssertionError`가 의도된 Red입니다.

```bash
uv run pytest -q labs/exercises/tests/test_ge_summary.py -m current_goal
```

`labs/exercises/ge_summary.py`의 작은 필드 계산을 `is_publish_blocking_gate`의 의미에 맞게
고칩니다. `supports_publish_decision`은 게시 승인 결과가 아니라, 이 근거가
게시 결정을 담당할 수 있는지를 나타냅니다. 검증 설정이나 공식 근거를
수정하지 않으며, `NotImplementedError`를 추가하지 않습니다.

완료는 전체 연습이 통과하는 것으로 확인합니다.

```bash
uv run pytest -q labs/exercises/tests/test_ge_summary.py
```

14개가 통과하면, 품질 결과의 범위와 게시 담당 여부를 나눈 한 문장을 판단
기록의 데이터 품질 칸에 남깁니다. 막힐 때는
`labs/solutions/ge_summary.py`를 참고할 수 있지만, 정답
파일을 복사하는 명령으로 쓰지 않습니다.

## 2. 남는 시간 실습

데이터 역할을 구분하고, 원본 품질과 자동 검증을 판단 기록에 적은 뒤에만
엽니다. 여기서 계산한 지문은 “지금 폴더의 학습/검증 파일이 선언과 같은가”만
답합니다.

### 2-1. train/valid 파일 지문이 revision v2 선언과 같은지 계산한다

선택 노트북 `02_inspect_dvc_revision_practice.ipynb`를 위에서 아래로
실행합니다. 노트북은 저장소 루트를 찾아 `uv run dvc status`를 보고,
학습/검증 파일의 SHA-256을 직접 계산해 선언 파일과 대조합니다.
공식 평가용 `test`와 `operational` 파일은 열지 않습니다.
잠금 파일 지문이 달라도 값을 고치지 말고 계산 결과를 적습니다.
이 학습/검증 지문 확인은 2장 본편
`uv run python labs/run/log_development.py`에서 Compose MLflow에
`data_roles=train,valid`만 남기기 전에 먼저 닫는 전제입니다.

## 3. 단계 완료

판단 기록의 데이터 품질 칸에 역할 구분, 대표 품질 관찰, 검증 명령과 결과
범위를 남깁니다. 이 기록은 다음 장에서 같은 데이터 범위와 공식 평가 경계를
이어받는지 확인하는 근거입니다.
