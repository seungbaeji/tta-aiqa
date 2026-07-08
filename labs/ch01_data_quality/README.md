# 1-4. Pandas 기반 데이터 품질 확인 실습

Pandas 실습의 목표는 함수를 외우는 것이 아니라, 실행 결과를 보고 모델 평가 전제를 설명할 근거를 만드는 것입니다. 1-4에서는 데이터 로딩부터 품질 리포트 작성까지 실행하고, 각 출력값을 특성(feature) 품질, 라벨(label) 품질, 평가 전 제한 사항과 연결합니다.

이 Lab은 `data/vital_signs_evaluation_baseline.csv`를 기준 데이터로 삼아 운영 이상을 조사할 때 필요한 첫 확인 절차를 연습합니다. `high_risk` 비율 증가처럼 품질 이상 신호가 보이면, 모델을 보기 전에 데이터 구조, 입력값, 라벨, 클래스 분포가 평가를 지탱하는지 확인해야 합니다.

실습을 진행할 때는 다음 기준을 중심으로 확인합니다.

- 실습 확인 순서: 데이터 로딩, 스키마(schema) 확인, 결측치 확인, 이상치 확인, 라벨 분포 확인
- 실행 결과 해석: 출력값을 특성 품질, 라벨 품질, 평가 전제 판단과 연결
- 라벨 값 표준화 기준: `high_risk`, `low_risk`를 모델 평가의 정답 기준으로 사용
- 데이터 품질 리포트 활용: 평가 전제와 제한 사항을 설명하는 근거

이 Lab의 핵심은 데이터 로딩부터 품질 리포트까지의 출력을 모델 평가 전제 판단으로 바꾸는 것입니다. 문서는 각 출력의 의미와 QA 해석을 설명하고, Notebook은 같은 확인 흐름을 셀 단위로 실행해 보는 산출물입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch01_data_quality/README.md` | 실습 목적, 예상 출력, QA 해석을 순서대로 확인 |
| Notebook | `labs/ch01_data_quality/pandas_data_quality_lab.ipynb` | 데이터 로딩부터 evidence packet과 보고 문장 초안 생성까지 직접 실행 |
| CLI 스크립트 | `labs/ch01_data_quality/*.py` | Notebook과 같은 흐름을 명령행에서 단계별 실행 |

## 1-4-1. 데이터 분석 환경과 파일 불러오기

**첫 단계에서는 데이터를 읽는 것보다 평가 가능한 구조로 준비되었는지 확인하는 것이 중요합니다.** Pandas 실습은 모델 평가 전에 데이터 품질을 직접 확인하는 절차입니다. 중요한 목표는 모델을 학습시키는 것이 아니라, 모델 평가 지표를 신뢰할 수 있는 데이터 상태인지 확인하는 것입니다.

Pandas는 실습의 목적이 아니라 수단입니다. 교재에서 Pandas를 사용하는 이유는 데이터 품질 문제를 눈으로 확인하기 쉽고, 같은 확인 과정을 코드로 반복할 수 있기 때문입니다. 중요한 것은 `dataframe.isna()`나 `value_counts()` 함수를 외우는 것이 아니라, 그 결과를 보고 모델 평가 전제가 흔들리는지 설명하는 것입니다.

실습 예제는 “코드를 실행한다”에서 끝나지 않습니다. 각 실행 결과 뒤에는 그 결과가 특성 품질, 라벨 품질, 평가 전 제한 사항과 어떻게 연결되는지 해석합니다. 이런 해석이 있어야 데이터 탐색이 QA 활동이 됩니다.

이 단계의 첫 판단 질문은 실제로 기대한 데이터 파일을 읽고 있는가입니다. 앞에서 본 `high_risk` 예측 비율 증가 사건을 Lab 관점으로 바꾸면, 잘못된 파일을 읽거나 라벨 값 표준화가 적용되지 않은 상태에서 이후 결측치, 이상치, 평가 전제 해석이 모두 흔들린다는 점을 확인해야 합니다.

| 실습 항목 | 확인 이유 |
| --- | --- |
| 데이터 구조 | 필요한 컬럼이 모두 존재하는지 확인 |
| 결측치 | 특성과 라벨이 비어 있는지 확인 |
| 이상치 | 비정상 값이 입력 데이터 의미를 흔드는지 확인 |
| 라벨 분포 | 클래스(class) 불균형과 관심 클래스 표본 수(Positive support) 부족 여부를 확인 |
| 데이터 통계 | 데이터가 모델 평가에 적합한 상태인지 종합적으로 판단 |

| 사건의 원인 후보 | 이 Lab에서 확인할 출력 | 줄일 수 있는 오해 |
| --- | --- | --- |
| 잘못된 데이터 파일 사용 | `shape`, 주요 컬럼, 라벨 개수 | 모델 자체 문제가 아니라 입력 파일 문제일 가능 |
| 라벨 값 표준화 미적용 | `high_risk`, `low_risk` 분포 | 원본 라벨 표기 차이를 모델 자체 문제로 오해 |
| 필수 컬럼 누락 | 컬럼 목록 | 뒤 단계에서 생기는 오류 원인 추적 |

실습 코드는 문서 안에만 두지 않고 저장소의 실행 가능한 파일로 제공합니다. 문서에는 핵심 snippet만 보여 주고, 전체 코드는 아래 경로에서 확인합니다.

| 구분 | 경로 | 역할 |
| --- | --- | --- |
| 데이터 준비 | `labs/prepare_data.py` | Kaggle 원본 CSV에서 실습용 파생 CSV를 생성 |
| 스키마 설정 | `configs/validation/dataset_schema.yaml` | 컬럼명, 필수 컬럼, 특성, 라벨 기준을 정의 |
| 품질 규칙 | `configs/validation/data_quality_rules.yaml` | 허용 라벨, 수치 범위, 최소 관심 클래스 표본 수를 정의 |
| 공통 코드 | `packages/ai-quality/src/ai_quality/data_quality` | 데이터 품질 확인 domain, application, infrastructure 코드 위치 |
| 1장 실습 | `labs/ch01_data_quality` | 공통 코드를 호출하는 얇은 lab 스크립트 위치 |

실습 데이터 파일은 README의 파생 파일 중 기본 데이터 품질 확인용 파일인 `data/vital_signs_evaluation_baseline.csv`를 기준으로 둡니다. 원본 데이터는 Kaggle의 [Human Vital Sign Dataset](https://www.kaggle.com/datasets/nasirayub2/human-vital-sign-dataset)이며, 실습에서는 컬럼명을 교육용 스키마에 맞게 정리하고 라벨 값을 `high_risk`, `low_risk`로 맞춘 파일을 사용합니다.

Notebook으로 실습한다면 `labs/ch01_data_quality/pandas_data_quality_lab.ipynb`를 열고 첫 번째 셀부터 순서대로 실행합니다. 명령행에서 확인하려면 아래 CLI 스크립트를 같은 순서로 실행합니다. 두 방식 모두 같은 데이터와 공통 코드를 사용하므로, 출력값은 같은 기준으로 해석합니다.

이 순서는 파일 생성, 라벨 정리, 구조 확인을 분리해 이후 품질 판단의 근거를 남기기 위한 것입니다. 실습은 다음 순서로 진행합니다.

1. 원본 CSV에서 실습용 CSV를 생성합니다.
2. 실습용 CSV를 불러와 컬럼명을 정리하고 라벨 값을 맞춥니다.
3. `shape`, 주요 컬럼, 라벨 분포를 확인합니다.
4. 평가 가능한 데이터 구조인지 QA 관점으로 해석합니다.

실습용 CSV 생성은 이후 모든 품질 확인의 입력 기준을 고정합니다. 먼저 원본 CSV에서 실습용 CSV를 생성합니다.

```bash
uv run python labs/prepare_data.py
```

데이터를 불러온 뒤 컬럼명을 실습용 스키마에 맞게 정리하고 라벨 값을 맞추는 핵심 코드는 `packages/ai-quality/src/ai_quality/data_quality/infrastructure/pandas_dataset_reader.py`에 있습니다. 이미 `high_risk`, `low_risk`로 정리된 파일도 그대로 사용할 수 있도록 `label` 값은 `replace`로 다시 맞춥니다.

```python
def load_and_standardize_dataset(
    dataset_path: Path,
    schema: DatasetSchema,
) -> pd.DataFrame:
    """Load a CSV file and normalize column names and labels."""
    dataframe: pd.DataFrame = pd.read_csv(dataset_path)
    dataframe = dataframe.rename(columns=schema.column_rename_map)

    if schema.target_column in dataframe.columns:
        dataframe[schema.target_column] = dataframe[schema.target_column].replace(
            LABEL_MAP
        )

    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(
            dataframe["timestamp"],
            errors="coerce",
        )

    return dataframe
```

첫 번째 실습 파일은 데이터가 평가 가능한 구조로 읽히는지 확인합니다. Notebook에서는 `labs/ch01_data_quality/pandas_data_quality_lab.ipynb`의 데이터 로딩 셀을 실행합니다. 명령행에서 1장 리포트를 다시 만들 때는 `make lab-data-quality`를 사용합니다.

이 출력에서 확인할 핵심은 주요 특성과 정리된 `label` 값이 같은 데이터프레임 안에 있는지입니다. 예상 출력은 데이터의 앞부분, shape, 라벨 분포가 함께 보이는 형태입니다. 숫자는 데이터 생성 상태에 따라 조금 달라질 수 있습니다.

```text
[shape]
(20002, 17)

[label values]
label
high_risk    10416
low_risk      9586
```

| 확인 결과 | QA 해석 |
| --- | --- |
| `dataframe.head()`에 `heart_rate`, `oxygen_saturation`, `label` 등 주요 컬럼이 보임 | 파일 정상 로드 |
| `label` 값이 `high_risk`, `low_risk`로 정리됨 | 관심 클래스(Positive class)와 비교 클래스(Negative class) 기준을 사용 가능 |
| `shape`가 `(20002, 17)`로 출력됨 | 현재 기준 데이터의 행/열 수가 예상과 일치 |
| `high_risk`와 `low_risk` 개수가 출력됨 | 라벨 분포 확인 시작 가능 |

파일 경로 오류, 컬럼명 변경, 라벨 값 표준화 실패가 발생하면 이후 실습 결과도 신뢰하기 어렵습니다. 첫 단계에서는 데이터를 읽는 것보다 “평가 가능한 구조로 준비되었는가”를 확인하는 것이 중요합니다.

실패 시에는 데이터 생성 여부와 라벨 값 표준화 기준을 먼저 확인합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| `FileNotFoundError` | `labs/prepare_data.py` 실행 여부와 `data/vital_signs_evaluation_baseline.csv` 존재 여부 |
| 주요 컬럼이 보이지 않음 | Kaggle 원본 컬럼명과 스키마의 컬럼명 정리 규칙 일치 여부 |
| `High Risk`, `Low Risk`가 그대로 남음 | 라벨 값 표준화 적용 여부 |

이 단계에서 줄어든 원인 후보는 잘못된 파일 사용, 컬럼명 정리 실패, 라벨 값 표준화 누락입니다. 다음 단계에서는 파일이 맞다는 전제 위에서 필수 컬럼과 데이터 타입이 모델 평가에 필요한 확인 기준을 만족하는지 확인합니다.

## 1-4-2. 필수 컬럼과 데이터 타입 확인

**필수 컬럼과 데이터 타입은 모델 평가를 시작하기 위한 확인 기준입니다.** 필수 컬럼이 없으면 모델 평가를 진행할 수 없거나, 결과 해석이 제한됩니다.

필수 컬럼 확인은 데이터 파일의 “모양”을 보는 작업이 아닙니다. 모델 평가에 필요한 기준이 충족되는지 확인하는 작업입니다. 모델은 정해진 특성 목록을 입력으로 사용하고, 평가는 정해진 라벨을 기준으로 예측을 비교합니다. 따라서 특성이나 라벨 컬럼이 누락되면 이후 단계의 결과가 정상적으로 계산되더라도 그 의미를 신뢰하기 어렵습니다.

데이터 타입도 같은 관점에서 봐야 합니다. 숫자형 특성이 문자열로 들어오면 통계 요약, 범위 검증, 모델 입력 변환이 모두 흔들릴 수 있습니다. 시간 정보(timestamp)가 문자열 그대로 남아 있으면 시간대별 비교와 추적이 어려워질 수 있습니다. 타입 검사는 단순 형식 검사가 아니라 이후 품질 분석이 가능한 데이터 구조인지 확인하는 절차입니다.

1장의 품질 이상 사례처럼 예측 분포가 갑자기 변했다면, 필수 컬럼과 타입 확인은 가장 먼저 실행할 기본 관문입니다. API나 모델이 바뀌지 않았더라도 산소포화도(oxygen saturation)를 담는 `oxygen_saturation`이 문자열로 들어오거나 `timestamp`가 파싱되지 않으면 이후 분포 비교가 잘못될 수 있습니다.

필수 컬럼과 타입은 다음 순서로 확인합니다.

1. `required_columns`가 모두 존재하는지 확인합니다.
2. 모델 입력 특성과 `label`이 누락되지 않았는지 확인합니다.
3. 숫자형 특성, 시간 정보(timestamp), 라벨의 타입이 기대와 맞는지 확인합니다.
4. 누락이나 타입 오류가 모델 평가를 제한하는지 판단합니다.

```python
def find_missing_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> list[str]:
    """Return required columns that are missing from a dataframe."""
    return [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]


dataframe = load_chapter_dataframe()
schema = load_schema()

missing_columns = find_missing_columns(
    dataframe=dataframe,
    required_columns=list(schema.required_columns),
)

print(missing_columns)
```

`missing_columns`가 빈 리스트라면 필수 컬럼이 모두 존재하는 상태입니다.

전체 흐름은 `labs/ch01_data_quality/pandas_data_quality_lab.ipynb`에서 셀 단위로 실행합니다. 이 단계에서는 스키마 확인 셀을 실행합니다.

예상 출력에서 `[missing columns]` 아래에 빈 리스트가 보이면 스키마 기준의 필수 컬럼이 모두 존재한다는 뜻입니다.

```text
[missing columns]
[]

[dtypes]
patient_id                   int64
heart_rate                   int64
timestamp           datetime64[ns]
label                       object
```

| 누락 컬럼 | 영향 |
| --- | --- |
| `patient_id` | 샘플(sample) 추적 어려움 |
| `timestamp` | 시간 기반 비교와 추적 어려움 |
| `heart_rate` | 모델 입력 특성이 부족 |
| `oxygen_saturation` | 모델 입력 특성이 부족 |
| `label` | 평가 지표를 계산할 수 없음 |

데이터 타입은 범위 검증과 통계 요약이 신뢰 가능한지 확인하는 근거입니다. 데이터 타입도 함께 확인합니다.

```python
print(dataframe.dtypes)
```

| 컬럼 | 기대 타입 | 잘못된 타입일 때 문제 |
| --- | --- | --- |
| `patient_id` | 정수 또는 문자열 | 샘플 추적이 어려울 가능 |
| `timestamp` | datetime | 시간 기반 분석이 어려울 가능 |
| `heart_rate` | 숫자형 | 범위 검증과 모델 입력 처리가 어려울 가능 |
| `oxygen_saturation` | 숫자형 | 범위 검증과 모델 입력 처리가 어려울 가능 |
| `label` | 문자열 | 클래스 해석이 어려울 가능 |

| 확인 결과 | 사건 해석에 미치는 영향 |
| --- | --- |
| 필수 특성 모두 존재 | 입력 데이터 문제를 다음 단계에서 확인 가능 |
| 모델 입력 특성 누락 | 모델 입력 조건이 달라져 먼저 데이터 구조 보완 필요 |
| 숫자형 특성이 문자열 | 범위 검증(range check) 전 변환 로직 확인 필요 |
| `timestamp` 파싱 실패 | 특정 시간대 집중 여부를 판단하기 어려움 |

데이터 타입이 기대와 다르면 결측치나 이상치를 제대로 계산하지 못할 수 있습니다. 특히 숫자형 특성이 문자열로 들어오면 범위 검증과 통계 요약이 왜곡됩니다.

필수 컬럼과 타입 검사는 평가를 진행하기 어려운 데이터 구조를 찾는 강한 근거입니다. `label`이 없으면 모델 지표(metric)를 계산할 수 없고, 모델 입력 특성이 없으면 모델 입력이 학습 때와 달라집니다. 이런 상태에서 억지로 평가를 진행하면 모델 자체 문제와 데이터 구조 문제를 구분하기 어렵습니다.

실패 시에는 누락된 컬럼이 단순 메타데이터(metadata)인지, 모델 입력 특성인지, 라벨인지 먼저 구분합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| `missing_columns`에 `label` 포함 | 정답 기준 보완 필요성이 높음 |
| 모델 입력 특성 누락 | 데이터 추출 또는 컬럼명 정리 로직 확인 |
| 숫자형 특성이 문자열 | CSV 파싱, 단위 기호, 결측 표시값 확인 |

이 단계에서 줄어든 원인 후보는 스키마 불일치와 필수 입력 누락입니다. 다음 단계에서는 컬럼이 존재한다는 전제 위에서 값이 비어 있거나 특정 클래스에 치우쳐 누락되는지 확인합니다.

## 1-4-3. 결측치 확인

**결측치는 개수보다 위치가 중요합니다.** 모델 입력인지, 라벨인지, 특정 클래스에 집중되는지 함께 봐야 합니다.

결측치 확인에서 중요한 것은 “몇 개가 비었는가”만이 아닙니다. 어떤 컬럼이 비었는지, 그 컬럼이 모델 입력인지, 결측치가 특정 클래스에 집중되는지, 결측치가 평가 대상 행(row)을 얼마나 줄이는지 함께 봐야 합니다. 같은 1% 결측치라도 메타데이터(metadata) 컬럼의 결측치와 모델 입력 특성의 결측치는 품질 영향이 다릅니다.

라벨 결측치는 특성 결측치보다 더 강하게 다루어야 합니다. 특성 결측치는 경우에 따라 보정하거나 제한 사항을 남긴 평가가 가능할 수 있지만, 라벨이 없으면 예측과 정답을 비교할 수 없습니다. 이 경우 해당 행은 지표 계산에서 제외해야 할 수 있고, 제외 기준이 클래스 분포를 왜곡하지 않는지도 확인해야 합니다.

1장의 품질 이상 사례에서는 `high_risk` 비율이 달라졌기 때문에 결측치 확인이 중요합니다. 결측치가 전체적으로 조금 늘어난 것인지, `high_risk` 샘플이나 특정 특성에 집중된 것인지에 따라 QA 판단이 달라집니다.

```python
def build_missing_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "missing_count": dataframe.isnull().sum(),
            "missing_ratio": dataframe.isnull().mean() * 100,
        }
    ).sort_values(
        by="missing_ratio",
        ascending=False,
    )


missing_summary = build_missing_summary(dataframe)

print(missing_summary)
```

특성 결측치와 라벨 결측치는 구분해서 확인해야 합니다.

```python
feature_missing_summary = build_missing_summary(
    dataframe.loc[:, list(schema.model_feature_columns)]
)

label_missing_count = int(dataframe[schema.target_column].isnull().sum())

print(feature_missing_summary)
print(label_missing_count)
```

| 결측치 발생 위치 | QA 해석 |
| --- | --- |
| `heart_rate` | 모델 입력 정보가 부족해질 가능 |
| `respiratory_rate` | 호흡 관련 특성 정보가 부족해질 가능 |
| `body_temperature` | 체온 특성 기반 판단이 어려워질 가능 |
| `oxygen_saturation` | 주요 특성 누락으로 예측 품질이 흔들릴 가능 |
| `label` | 평가 지표를 신뢰하기 어려움 |
| `timestamp` | 시간 기반 비교가 어려워질 가능 |

| 결측치 패턴 | 사건에서의 의미 | QA 판단 |
| --- | --- | --- |
| 모델 입력 특성에 고르게 낮은 비율 | 제한 사항으로 기록 가능 | 모델 평가 전 제한 사항 기록 |
| `high_risk` 샘플에 집중 | 관심 클래스 평가가 불안정 | 모델 평가 전 제한 사항 기록 |
| `label` 결측 존재 | 정답 비교 불가 | 해당 행 제외 기준과 라벨 생성 로직 확인 |
| 특정 시간대에 집중 | 수집 경로 문제 가능 | 운영 로그와 함께 확인 |

결측치 확인은 다음 순서로 진행합니다.

1. 전체 컬럼의 결측치 개수와 비율을 확인합니다.
2. 모델 특성의 결측치만 따로 확인합니다.
3. `label` 결측치가 있는지 별도로 확인합니다.
4. 결측치가 있는 행을 살펴보고 클래스 집중 여부를 판단합니다.

결측치가 어떤 행과 라벨에 집중되는지 확인해야 평가 제외 기준을 판단할 수 있습니다. 결측치가 있는 행도 확인합니다.

```python
rows_with_missing_values = dataframe[
    dataframe.loc[:, list(schema.required_columns)].isnull().any(axis=1)
]

print(rows_with_missing_values.head())
```

결측치가 있는 행이 특정 라벨에 몰려 있는지도 함께 확인합니다.

```python
def build_affected_label_counts(
    dataframe: pd.DataFrame,
    label_column: str,
) -> pd.Series:
    if dataframe.empty or label_column not in dataframe.columns:
        return pd.Series(dtype="int64", name="count")
    return dataframe[label_column].value_counts(dropna=False)


affected_label_counts = build_affected_label_counts(
    dataframe=rows_with_missing_values,
    label_column=schema.target_column,
)

print(affected_label_counts)
```

전체 흐름은 `labs/ch01_data_quality/pandas_data_quality_lab.ipynb`에서 셀 단위로 실행합니다. 이 단계에서는 결측치 확인 셀을 실행합니다.

이 출력에서 확인할 핵심은 모델 입력 특성과 라벨에 결측이 없는지입니다. 예상 출력은 전체 컬럼, 모델 입력 특성, 라벨 결측치를 나누어 보여줍니다. 전체 결측 비율만 보지 말고, 어떤 컬럼과 어떤 라벨 구간에 결측치가 있는지 확인해야 합니다.

```text
[model features]
                          missing_count  missing_ratio
heart_rate                            0            0.0
respiratory_rate                      0            0.0
body_temperature                      0            0.0
oxygen_saturation                     0            0.0
systolic_blood_pressure               0            0.0
diastolic_blood_pressure              0            0.0

[label missing count]
0

[rows with missing values]
Empty DataFrame

[labels in rows with missing values]
Series([], Name: count, dtype: int64)
```

결측치 확인은 이후 모델 평가와도 연결됩니다. 특성 결측치가 많아지면 모델 입력 조건이 달라지므로, 모델 지표를 해석할 때 제한 사항으로 남겨야 합니다.

결측치 보고서에는 결측치 수와 비율뿐 아니라 판단도 함께 남깁니다. 예를 들어 “`heart_rate` 결측치 42건”보다 “모델 입력 특성인 `heart_rate` 결측치 42건이 확인되어 평가 해석에 제한이 있습니다”처럼 적어야 합니다. 이 기록이 있어야 모델 지표를 볼 때 데이터 문제와 모델 자체 문제를 분리할 수 있습니다.

실패 시에는 결측치의 위치와 집중도를 확인합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 라벨 결측치 존재 | 지표 계산 제외 기준과 라벨 생성 로직 확인 |
| 특정 특성 결측치 집중 | 해당 특성이 모델 입력인지 확인 |
| 특정 클래스에 결측치 집중 | 관심 클래스와 비교 클래스 평가 영향 확인 |

이 단계에서 줄어든 원인 후보는 입력 정보 부족과 라벨 결측으로 인한 평가 전제 훼손입니다. 다음 단계에서는 값이 존재하더라도 허용 범위를 벗어나 데이터 의미를 왜곡할 수 있는지 확인합니다.

## 1-4-4. 이상치 탐지

**이상치 탐지는 극단값을 무조건 제거하기 위한 절차가 아니라, 평가 해석을 흔들 수 있는 입력 오류를 찾는 절차입니다.** 먼저 숫자형 컬럼의 기본 통계를 확인합니다. 범위 검증 대상 컬럼은 `configs/validation/data_quality_rules.yaml`에서 읽어옵니다.

이상치는 단순히 평균에서 멀리 떨어진 값이 아닙니다. QA 관점에서는 “모델이 실제 신호로 받아들이면 안 되는 값” 또는 “수집, 변환, 단위 처리 과정에서 오류가 의심되는 값”을 찾는 것이 핵심입니다. 그래서 이상치 기준은 데이터의 의미와 실습용 검증 규칙(rule)을 함께 봐야 합니다.

이상치 발견은 삭제 결정이 아니라 평가 제한 사항을 기록하는 근거입니다. 일부 극단값은 실제로 드물지만 가능한 값일 수 있고, 일부 값은 명백한 수집 오류일 수 있습니다. QA는 값을 제거하는 결정보다 먼저, 어떤 규칙(rule)으로 탐지했는지와 그 값이 평가 해석에 어떤 영향을 줄 수 있는지 기록해야 합니다.

1장의 품질 이상 사례에서 `high_risk` 예측 비율이 올라갔다면, 이상치 탐지는 “입력값 자체에 불가능한 값이 섞였는가”를 확인하는 단계입니다. 특히 `oxygen_saturation = 135`처럼 숫자 타입은 맞지만 의미상 불가능한 값은 API 스키마만으로는 걸러지지 않을 수 있습니다.

```python
rules = load_rules()
valid_ranges = {
    rule.column: (rule.min_value, rule.max_value)
    for rule in rules.valid_ranges
}
numeric_columns = [
    column
    for column in valid_ranges
    if column in dataframe.columns
]

print(dataframe.loc[:, numeric_columns].describe())
```

실습용 오류 탐지 범위를 정의합니다. 이 범위는 의료적 판단 기준이 아니라, 명백히 잘못된 값을 찾기 위한 예제용 검증 기준입니다.

```yaml
valid_ranges:
  heart_rate:
    min: 1
    max: 250
  oxygen_saturation:
    min: 0
    max: 100
```

이상치 확인은 다음 순서로 진행합니다.

1. 숫자형 특성의 기본 통계를 확인합니다.
2. 검증 규칙(rule)의 허용 범위를 확인합니다.
3. 허용 범위를 벗어난 값의 개수와 비율을 계산합니다.
4. 실제 극단값인지 수집 또는 변환 오류인지 판단합니다.

컬럼별 이상치 개수와 비율을 확인합니다.

```python
def build_outlier_summary(
    dataframe: pd.DataFrame,
    valid_ranges: dict[str, tuple[float, float]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for column, (min_value, max_value) in valid_ranges.items():
        values = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_mask = values.notna() & (
            (values < min_value) | (values > max_value)
        )

        invalid_count = int(invalid_mask.sum())
        invalid_ratio = (
            invalid_count / len(dataframe) * 100
            if len(dataframe) > 0
            else 0.0
        )

        rows.append(
            {
                "column": column,
                "min_value": min_value,
                "max_value": max_value,
                "invalid_count": invalid_count,
                "invalid_ratio": invalid_ratio,
            }
        )

    return pd.DataFrame(rows)


outlier_summary = build_outlier_summary(dataframe, valid_ranges)

print(outlier_summary)
```

허용 범위를 벗어난 행이 있다면 라벨 분포도 함께 확인합니다.

```python
def build_outlier_label_summary(
    dataframe: pd.DataFrame,
    valid_ranges: dict[str, tuple[float, float]],
    label_column: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    if label_column not in dataframe.columns:
        return pd.DataFrame(columns=["column", "label", "invalid_count"])

    for column, (min_value, max_value) in valid_ranges.items():
        if column not in dataframe.columns:
            continue

        values = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_mask = values.notna() & (
            (values < min_value) | (values > max_value)
        )
        label_counts = dataframe.loc[invalid_mask, label_column].value_counts(
            dropna=False
        )

        for label, count in label_counts.items():
            rows.append(
                {
                    "column": column,
                    "label": label,
                    "invalid_count": int(count),
                }
            )

    return pd.DataFrame(rows, columns=["column", "label", "invalid_count"])


outlier_label_summary = build_outlier_label_summary(
    dataframe=dataframe,
    valid_ranges=valid_ranges,
    label_column=schema.target_column,
)

print(outlier_label_summary)
```

전체 흐름은 `labs/ch01_data_quality/pandas_data_quality_lab.ipynb`에서 셀 단위로 실행합니다. 이 단계에서는 이상치 확인 셀을 실행합니다.

이 출력에서 확인할 핵심은 허용 범위 초과가 주요 모델 입력 특성에 있는지입니다. 예상 출력은 검증 규칙(rule)별 허용 범위 초과 건수와 비율을 보여주는 형태입니다. 실제 실행 결과에는 `data_quality_rules.yaml`에 정의된 모든 범위 규칙이 출력되며, 아래 예시는 그중 일부를 발췌한 것입니다.

```text
                     column  min_value  max_value  invalid_count  invalid_ratio
0                heart_rate        1.0      250.0              0            0.0
3         oxygen_saturation        0.0      100.0              0            0.0

[labels in outlier rows]
Empty DataFrame
Columns: [column, label, invalid_count]
Index: []
```

| 이상치 예시 | 의심 가능한 원인 |
| --- | --- |
| `heart_rate = -999` | 오류값 또는 수집 실패값일 수 있음 |
| `oxygen_saturation = 135` | 허용 범위 초과 데이터 |
| `body_temperature = 120` | 단위 오류 또는 파싱 오류를 의심 가능 |
| `height_m = 0` | 입력 오류 또는 기본값 저장 가능성이 있음 |

| 이상치 결과 | 사건에서의 원인 후보 | 다음 확인 |
| --- | --- | --- |
| 허용 범위 초과 건수 없음 | 데이터 범위 오류 가능성 낮음 | 라벨, 클래스 비율 |
| 특정 특성의 허용 범위 초과 증가 | 입력 수집 또는 단위 변환 문제 | 원본 데이터 출처와 시간 정보(timestamp) |
| 특정 클래스에 허용 범위 초과 집중 | 특정 클래스 평가 신뢰도 저하 가능 | 클래스별 허용 범위 초과 비율 |
| 운영에서만 허용 범위 초과 증가 | 평가 데이터와 운영 입력 차이 가능 | 서빙 입력 스키마 |

이상치는 모델 입력의 의미를 왜곡할 수 있습니다. 예를 들어 비정상적으로 큰 값이나 불가능한 음수 값이 많아지면 해당 샘플의 예측을 신뢰하기 어려울 수 있습니다.

이상치 결과는 운영 관측과 승인 판단으로도 이어집니다. 운영에서 특정 특성의 입력 분포가 갑자기 바뀌면 예측 분포도 함께 변할 수 있습니다. 1장에서 이상치 기준을 명확히 두면 운영 대시보드에서 어떤 변화를 경고 신호로 볼지 판단하기 쉬워집니다.

실패 시에는 이상치가 실제 극단값인지 데이터 오류인지 구분합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 허용 범위 초과 값 존재 | 단위 오류, 파싱 오류, 오류 코드 여부 |
| 특정 시간대에 이상치 집중 | 수집 장비나 입력 경로 문제 가능성 |
| 특정 클래스에 이상치 집중 | 특정 클래스 평가가 흔들릴 가능성 |

이 단계에서 줄어든 원인 후보는 비정상 입력값과 수집 오류입니다. 다음 단계에서는 데이터 값 자체가 아니라 정답 기준인 라벨과 관심 클래스 표본 수가 모델 평가를 지탱할 수 있는지 확인합니다.

## 1-4-5. 라벨 분포와 관심 클래스 표본 수 확인

**라벨은 모델 평가의 정답 기준이고, 관심 클래스 표본 수는 관심 클래스를 평가할 표본 수입니다.** 라벨 분포 확인은 모델 평가 전에 정답 기준과 표본 구성이 충분한지 함께 보는 단계입니다.

분류(classification)는 샘플을 정해진 클래스 중 하나로 나누는 문제입니다. 이 실습의 이진 분류(binary classification)에서는 `high_risk`와 `low_risk` 두 클래스를 사용하고, 모델 평가는 예측을 실제 정답 라벨과 비교합니다.

라벨은 지표의 기준점입니다. 특성이 모델의 입력이라면 라벨은 모델 결과를 평가하는 정답입니다. 라벨 값이 허용 목록과 다르거나 관심 클래스와 비교 클래스 기준이 뒤바뀌면 지표는 계산되더라도 잘못된 의미를 갖습니다.

관심 클래스 표본 수는 특히 `high_risk`처럼 QA가 관심 있게 보는 클래스의 샘플 수를 의미합니다. 이 값이 너무 적으면 모델 평가 결과가 일부 샘플에 과도하게 흔들릴 수 있습니다.

1장의 품질 이상 사례에서 `high_risk` 예측 비율이 늘어났다면 라벨 분포 확인은 두 가지를 구분하게 해 줍니다. 실제 평가 데이터에 `high_risk` 라벨이 늘어난 것인지, 모델 예측만 늘어난 것인지, 또는 라벨 기준이 흔들린 것인지 확인해야 합니다.

라벨 확인은 다음 순서로 진행합니다.

1. 라벨별 개수와 비율을 확인합니다.
2. 허용되지 않은 라벨과 결측 라벨이 있는지 확인합니다.
3. 관심 클래스 표본 수인 `high_risk` 표본 수를 확인합니다.
4. 클래스 불균형이 평가 결과 해석에 미치는 영향을 판단합니다.

라벨별 개수와 비율은 관심 클래스 평가가 안정적인지 판단하는 기본 근거입니다. 먼저 라벨별 개수와 비율을 확인합니다.

```python
label_count = dataframe[schema.target_column].value_counts(dropna=False)
label_ratio = (
    dataframe[schema.target_column].value_counts(normalize=True, dropna=False)
    * 100
)

print(label_count)
print(label_ratio)
```

허용되지 않은 라벨이 있는지 확인합니다.

```python
support = calculate_label_support(list(dataframe[schema.target_column]))

print(support.invalid_count)
print(support.missing_count)
```

관심 클래스 표본 수를 확인합니다.

```python
print(support.positive_count)
print(support.negative_count)
print(f"{support.positive_rate:.2f}%")
```

전체 흐름은 `labs/ch01_data_quality/pandas_data_quality_lab.ipynb`에서 셀 단위로 실행합니다. 이 단계에서는 라벨 분포 확인 셀을 실행합니다.

이 출력에서 확인할 핵심은 `high_risk`와 `low_risk`가 허용 라벨로 충분히 확보되었는지입니다. 예상 출력은 라벨별 개수, 비율, 관심 클래스 표본 수, 허용되지 않은 라벨 수를 함께 보여줍니다.

```text
[label counts]
label
high_risk    10416
low_risk      9586

[label ratios]
label
high_risk    52.552245
low_risk     47.447755

[support]
LabelSupport(positive_label='high_risk', negative_label='low_risk', positive_count=10416, negative_count=9586, invalid_count=0, missing_count=0)
positive_rate=52.55%
```

| 항목 | 의미 | QA 관점 |
| --- | --- | --- |
| 관심 클래스 표본 수 | `high_risk` 샘플 수 | 관심 클래스 평가 안정성과 연결됨 |
| 비교 클래스 표본 수 | `low_risk` 샘플 수 | 비교 클래스 평가 안정성과 연결됨 |
| 관심 클래스 비율(Positive rate) | 전체 중 `high_risk` 비율 | 클래스 불균형 여부를 확인 |

| 라벨 확인 결과 | 사건 해석 |
| --- | --- |
| 관심 클래스 표본 수 충분, 예측만 증가 | 모델 출력, 운영 기준, 입력 특성 변화 후보 |
| 관심 클래스 표본 수 자체가 크게 증가 | 평가 데이터 구성 또는 운영 입력 변화 후보 |
| 허용되지 않은 라벨 존재 | 라벨 값 표준화 규칙 또는 원본 표기 문제 |
| 한쪽 클래스만 존재 | 모델 평가 해석 어려움 또는 평가 데이터 재구성 후보 |

관심 클래스 표본 수가 너무 적으면 전체 정확도(Accuracy)는 높게 나올 수 있지만, 중요한 클래스 탐지 품질을 제대로 판단하기 어렵습니다. 세부 지표를 계산하기 전에 관심 클래스 표본 수가 평가를 지탱할 만큼 충분한지 확인해야 합니다.

허용되지 않은 라벨이 발견되면 단순 경고로 넘기지 않아야 합니다. 라벨 오류는 모델의 정답 기준을 흔들기 때문에 평가 전에 먼저 확인해야 할 핵심 사유가 됩니다. 이때 QA는 원본 라벨, 라벨 값 표준화 규칙, 정리 후 라벨 분포를 함께 확인해 어디에서 오류가 발생했는지 추적해야 합니다.

실패 시에는 원본 라벨 표기와 라벨 값 표준화 기준을 함께 확인합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| `invalid_count > 0` | 허용 라벨 목록과 원본 라벨 표기 차이 |
| 관심 클래스 표본 수 부족 | 관심 클래스 평가 안정성 |
| 한쪽 클래스만 존재 | 평가 데이터 구성 또는 라벨 값 표준화 오류 |

이 단계에서 줄어든 원인 후보는 라벨 기준 오류와 관심 클래스 표본 수 부족입니다. 다음 단계에서는 지금까지의 확인 결과를 통계 요약과 리포트로 묶어, 1-5에서 판단 문장을 작성할 근거를 준비합니다.

## 1-4-6. 데이터 통계 요약과 품질 리포트 생성

**통계 요약은 데이터 탐색의 끝이 아니라, 평가 전제를 설명할 근거를 문서화하는 시작점입니다.** 앞에서 확인한 결측치, 이상치, 라벨 분포를 종합하여 데이터가 모델 평가에 적합한 상태인지 설명할 자료를 만듭니다.

평균, 표준편차, 최솟값, 최댓값은 그 자체로 결론이 아닙니다. 이 값들이 기준선(baseline) 데이터와 크게 다른지, 허용 범위를 벗어나는지, 특정 특성에 품질 이슈가 집중되는지를 설명할 수 있어야 합니다.

특히 파생 특성은 통계 요약에서 별도로 보아야 합니다. 현재 모델 입력 특성은 `dataset_schema.yaml`의 `model_feature_columns`를 기준으로 확인하고, `derived_bmi`, `derived_map` 같은 파생 특성은 현재 모델 입력으로 해석하지 않습니다. 1장에서는 파생 특성의 존재 여부와 계산 기준 확인 필요성을 기록하고, 운영에서 같은 값을 만들 수 있는지는 별도 확인 대상으로 남깁니다.

요약 단계에서는 다음을 함께 확인합니다.

1. 숫자형 특성의 기본 통계를 확인합니다.
2. 현재 모델 입력 특성과 파생 특성을 구분합니다.
3. 컬럼별 데이터 타입(dtype), 결측치, 고유값 수를 정리합니다.
4. 실습 리포트의 확인값과 세부 결과를 근거로 QA 해석 코멘트를 준비합니다.

1장의 품질 이상 사례와 연결하면 통계 요약은 “원인 후보를 얼마나 줄였는가”를 정리하는 단계입니다. 스키마, 결측치, 이상치, 라벨 분포와 관심 클래스 표본 수가 안정적이라면 모델 지표 해석으로 넘어갈 수 있습니다. 반대로 데이터 품질 문제가 확인되면 모델 평가 결과를 바로 신뢰하지 않고 제한 사항을 남겨야 합니다.

숫자형 특성의 기본 통계는 모델 입력 분포가 평가 전제를 흔들지 않는지 보는 근거입니다. 숫자형 특성의 기본 통계를 확인합니다.

```python
feature_summary = dataframe.loc[:, list(schema.model_feature_columns)].describe()

print(feature_summary)
```

파생 특성의 통계도 별도로 확인합니다. 이 값은 현재 모델 지표의 직접 근거가 아니라, 이후 입력 특성 후보나 데이터 생성 과정 점검에 사용할 참고 정보입니다.

```python
derived_feature_summary = dataframe.loc[
    :, list(schema.derived_feature_columns)
].describe()

print(derived_feature_summary)
```

파생 특성은 현재 모델 입력에서는 제외되어 있지만, 이후 모델 입력 후보가 될 수 있습니다. 그 경우 계산식과 생성 시점이 분명해야 합니다.

| 특성 유형 | 예시 | QA 관점 |
| --- | --- | --- |
| 현재 모델 입력 특성 | `heart_rate`, `oxygen_saturation` | 모델 입력의 기본 품질을 확인 |
| 파생 특성 | `derived_bmi`, `derived_map` | 현재 모델 입력에서는 제외하고 계산식과 생성 시점 확인 |
| 메타데이터(metadata) | `timestamp`, `patient_id` | 추적과 분석에는 유용하지만 모델 입력으로는 주의가 필요 |

전체 데이터 품질 요약 테이블을 만듭니다.

```python
def summarize_column_quality(dataframe: pd.DataFrame) -> pd.DataFrame:
    summary: pd.DataFrame = pd.DataFrame(index=dataframe.columns)

    summary["dtype"] = dataframe.dtypes.astype(str)
    summary["missing_count"] = dataframe.isnull().sum()
    summary["missing_ratio"] = dataframe.isnull().mean() * 100
    summary["unique_count"] = dataframe.nunique(dropna=True)

    return summary


quality_summary = summarize_column_quality(dataframe)

print(quality_summary)
```

이 요약 테이블은 데이터 품질 상태를 빠르게 확인하는 데 유용합니다.

| 확인 항목 | 의미 | QA 해석 |
| --- | --- | --- |
| `dtype` | 데이터 타입 | 특성과 라벨이 기대 타입인지 확인 |
| `missing_count` | 결측치 개수 | 입력 또는 정답 누락 여부를 확인 |
| `missing_ratio` | 결측치 비율 | 품질 문제가 심각한지 판단 |
| `unique_count` | 고유값 개수 | 라벨 값 이상 또는 식별자 중복 가능성 확인 |

요약 테이블을 읽을 때는 한 컬럼씩 독립적으로 보지 않습니다. 결측치가 많은 특성, 이상치가 있는 특성, 고유값 수가 비정상적인 특성이 같은 영역에 모여 있다면 데이터 생성이나 전처리 과정의 공통 원인을 의심할 수 있습니다. 이런 관점이 있어야 데이터 품질 확인 결과가 단순 통계표가 아니라 품질 원인 분석의 출발점이 됩니다.

마지막 실습 스크립트는 앞의 확인 결과를 보고서에 인용 가능한 `QualityReport`로 묶습니다. Markdown 리포트 생성 명령은 다음과 같습니다.

```bash
uv run python labs/ch01_data_quality/build_quality_report.py
```

이 리포트에서 확인할 핵심은 평가 전제 충족 여부를 세부 근거로 설명할 수 있는지입니다. 예상 리포트에는 데이터 규모, 누락 컬럼, 관심 클래스 표본 수, 라벨 오류, 범위 검증 결과, 실습용 기본 전제 확인값이 함께 정리됩니다. 실제 리포트의 범위 검증(Range Checks)에는 모든 검증 대상 컬럼이 나오며, 아래 예시는 일부를 발췌한 것입니다. 리포트를 읽을 때는 `기본 평가 전제 충족`을 먼저 결론처럼 보지 말고, 세부 근거를 먼저 확인합니다.

```text
# 1장 데이터 품질 리포트

- 행 수: 20002
- 컬럼(column) 수: 17
- 누락 필수 컬럼: 없음
- 기본 평가 전제 충족: True

## 라벨 표본 수(Label Support)

| 항목 | 건수(count) |
| --- | --- |
| `high_risk` | 10416 |
| `low_risk` | 9586 |
| `invalid` | 0 |
| `missing` | 0 |

## 범위 검증(Range Checks)

| 컬럼(column) | 범위 초과 건수(invalid_count) | 범위 초과 비율(invalid_ratio) |
| --- | --- | --- |
| `heart_rate` | 0 | 0.00% |
| `oxygen_saturation` | 0 | 0.00% |
```

| 산출물 또는 필드 | QA 활용 |
| --- | --- |
| `artifacts/reports/chapter_01_quality_report.md` | 데이터 품질 확인 결과를 모델 평가 전 검토 자료로 사용 |
| 행 수, 컬럼(column) 수 | 평가 대상 데이터 규모가 예상과 같은지 확인 |
| 누락 필수 컬럼 | 필수 컬럼 누락 여부를 판단 |
| 라벨 표본 수(Label Support) | 관심 클래스 표본 수와 라벨 오류를 판단 |
| 범위 검증(Range Checks) | 명백한 범위 오류가 있는지 판단 |
| 기본 평가 전제 충족 | 위 조건을 간단히 묶어 보여주는 1-4 실습용 편의 확인값 |

리포트를 읽을 때는 `기본 평가 전제 충족` 하나로 결론을 끝내지 않습니다. 이 값은 업계 표준 용어가 아니라 1-4 실습 리포트의 편의 확인값입니다. 필수 컬럼, 라벨 오류, 관심 클래스 표본 수, 범위 오류를 함께 읽고, 1-5에서 실제 QA 코멘트로 바꿉니다.

실패 시에는 리포트 파일 생성 여부보다 리포트에 들어간 세부 근거를 먼저 확인합니다.

| 실패 현상 | 확인 포인트 |
| --- | --- |
| 리포트 파일이 생성되지 않음 | `data/vital_signs_evaluation_baseline.csv` 존재 여부, `artifacts/reports` 생성 권한, 스크립트 오류 메시지 |
| `기본 평가 전제 충족`이 `False`로 출력됨 | 필수 컬럼, 라벨, 관심 클래스 표본 수, 범위 검증 중 어떤 항목이 실패했는지 확인 |
| 리포트의 행 수나 라벨 분포가 예상과 다름 | `labs/prepare_data.py` 재실행 여부, 원본 CSV, 라벨 값 표준화 기준 |
| 범위 검증 값이 예상과 다름 | `configs/validation/data_quality_rules.yaml`의 허용 범위와 실제 입력값 단위 |

이 단계에서 만들어진 리포트는 1-5의 입력입니다. 리포트는 결론이 아니라 판단 근거이며, 다음 문서에서는 이 결과를 실제 QA 코멘트와 모델 평가 전 의사결정으로 바꿉니다.
