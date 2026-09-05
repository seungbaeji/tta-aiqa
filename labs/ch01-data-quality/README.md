# 1장 데이터 품질

이 장은 9단계 여정의 **데이터** 단계입니다. 첫 사건인 [배포된 baseline 관찰](../README.md#배포된-baseline-관찰)은
[`labs/README.md`](../README.md)에서 먼저 닫습니다.

## 데이터

이 장의 노트북과 검증 명령은 raw measurement에서 patient-level split과 GE
evidence로 이어집니다. sealed `test`는 학습 활동에서 열지 않습니다.

### train·valid·sealed test·operational의 역할을 누수 없이 구분한다

`uv run dvc status`로 현재 흐름을 확인하고
`data/splits/physionet-2012/revisions/v2/split-manifest.csv`를 읽습니다.
현재 역할은 `train 2,900 / valid 600 / test 400 / operational 100`입니다.
실행 전에 개발, 봉인 평가와 정답 없는 운영 표본의 역할을 예측한 뒤 분할 선언과
대조합니다. 이전 분할 `2,400 / 600 / 600 / 400`을 현재 지표에 섞지 않습니다.

```bash
uv run dvc status
```

### PhysioNet raw measurement의 결측·범위·join을 데이터 품질 근거로 해석한다

`01_physionet_data_quality_eda.ipynb`를 위에서 아래로 실행해 record별 측정 행,
`-1` 결측 표식, 48시간 범위, 4,000개 outcome join, 133개 특성과 결측률을 봅니다.
IQR 범위 밖 기록을 자동 삭제하지 않고, 관측 근거와 규약 위반을 구분해 E-02에
기록합니다. 특성 선택과 모델 조정은 하지 않습니다.

공식 원본과 개별 기록 단위 표를 다시 만들어야 할 때만 다음 명령을 실행합니다.

```bash
uv run python scripts/prepare_data.py
```

### GE summary가 데이터 품질 관찰을 재현 가능한 evidence로 닫는지 판단한다

EDA에서 확인한 raw/processed 규칙을 다음 명령으로 실행합니다.

```bash
uv run python scripts/validate_data.py
```

실행 후 `artifacts/data-quality/great-expectations/validation-summary.json`과
Data Docs가 생성됩니다. GE 결과는 데이터 품질 근거이지 DVC publish gate,
모델 승인 또는 target sync PASS가 아닙니다. 실행하지 못하면 `offline` 또는
`BLOCKED`로 기록하고 `docs/reference/evidence/data-quality/`와
`docs/reference/evidence/data-lineage/split-revision-v2.json`을 읽기 전용으로
사용합니다.

실행 결과 또는 reference evidence를 먼저 읽은 뒤, 학생이 편집할 파일
`labs/exercises/ge_summary/interpret.py`와 테스트
`labs/exercises/tests/test_ge_summary.py`를 확인합니다. 이 exercise의 함수는
GE를 실행하거나 파일을 쓰지 않고 reviewable summary mapping을 해석합니다.

예상은 `success=true`여도 `publish_blocking_gate=false`이면 이 evidence가
publish 결정을 담당하지 않는다는 것입니다. 시작 상태를 확인합니다.

```bash
uv run pytest -q labs/exercises/tests/test_ge_summary.py -m regression
```

regression 표시는 12개가 통과해야 합니다. 이어서 current goal을 실행하면
시작 상태의 두 `AssertionError`가 의도된 Red입니다.

```bash
uv run pytest -q labs/exercises/tests/test_ge_summary.py -m current_goal
```

`interpret.py`의 작은 필드 계산을 `is_publish_blocking_gate`의 의미에 맞게
고칩니다. `supports_publish_decision`은 publish 승인 결과가 아니라 이 evidence가
publish 결정을 담당할 수 있는지를 나타냅니다. GE/config/canonical evidence를
수정하거나 publish policy를 새로 구현하지 않으며, `NotImplementedError`를
추가하지 않습니다.

완료는 전체 exercise가 통과하는 것으로 확인합니다.

```bash
uv run pytest -q labs/exercises/tests/test_ge_summary.py
```

14개가 통과하면 quality result scope와 `supports_publish_decision`을 분리한
한 문장을 E-02에 남깁니다. 막힐 때는
`labs/exercises/solutions/ge_summary/interpret.py`를 instructor/reference
implementation으로 비교할 수 있지만, 정답 파일을 복사하는 명령으로 사용하지
않습니다.

## 단계 완료

`release-decision-record.md`의 E-02에 split 역할, 대표 품질 관찰, GE 명령과
summary 범위를 남깁니다. 이 기록은 다음 **모델** 단계가 같은 데이터 범위와
봉인 경계를 이어받는지 확인하는 근거입니다.
