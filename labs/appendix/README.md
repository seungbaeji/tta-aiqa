# Appendix A. EDA 도구 API 빠른 실습

## 1. 목적

이 appendix는 Python 객체와 container, `pandas`의 객체 모델과 핵심 데이터 변환,
NumPy 배열 규칙, `matplotlib`의 Figure/Axes 구조를 먼저 다룬다. 이어서 EDA와
Feature Engineering의 기본 원리, Great Expectations, DVC, scikit-learn과 MLflow를
사용해 데이터 이해부터 model workflow와 artifact provenance까지 연습한다. 각 notebook은 작은 합성 데이터와
임시 local storage를 사용하므로 canonical DVC data, model bundle, 외부 서비스 없이
실행할 수 있다. API를 암기하기보다 객체와 반환값을 확인하고 data가 validation,
pipeline, Run과 versioned artifact로 이어지는 흐름을 이해하는 데 집중한다.

각 notebook의 `## 3. Steps`는 `### 3-x`에서 관련 개념을 묶고,
`#### 3-x-y`에서 하나의 설명과 실행 예제를 다룬다. 따라서 큰 개념을 먼저 읽은 뒤
필요한 세부 API 단위로 다시 찾아볼 수 있다.

## 2. Notebook 순서

### 2-1. 데이터 분석을 위한 Python 기초

[데이터 분석을 위한 Python 기초](01_python_basics.ipynb)에서 기본 문법을 익힌 뒤
Python Data Model의 identity·type·value와 name binding을 살펴본다. mutable과
immutable, shallow/deep copy, hashability, 함수 인자의 객체 공유, special method
protocol을 실습하고 list·tuple·dict·set, slicing, 반복, 함수와 예외로 이어 간다. 이후
notebook에서 pandas 객체의 변경과 복사 동작을 판단하기 위한 기반이다.

### 2-2. pandas 객체와 핵심 API

[pandas 객체와 핵심 API](02_pandas_basics.ipynb)에서 `Series`, `DataFrame`,
`Index`의 관계와 label 정렬을 먼저 익힌다. 이후 `eq`, `lt`, `ge`, `between`, `isin`을
이용한 조건 선택, 결측값과 dtype 변환, 문자열 정리, 범주화, 중복 제거, `merge`,
`melt`, `pivot`, 시간 관련 Index, `MultiIndex`, `GroupBy`까지 전처리 흐름을 연결한다.
ch01 EDA의 raw 행 선택, 품질 점검, 시간 집계와 patient-level 요약을 읽기 위한 기반이다.

### 2-3. pandas 이해를 위한 NumPy 기초

[pandas 이해를 위한 NumPy 기초](03_numpy_basics.ipynb)에서 `ndarray`, shape, dtype,
indexing, view와 copy, axis reduction, broadcasting, vectorized 연산을 앞에서 배운
pandas 객체와 나란히 비교한다. NumPy의 위치·shape 계산과 pandas의 label alignment
차이, `np.nan`과 nullable dtype, `np.where`와 `Series.where`, `to_numpy`와
`Series.array` 변환 경계도 확인한다.

### 2-4. Matplotlib Figure와 Axes 기초

[Matplotlib Figure와 Axes 기초](04_matplotlib_basics.ipynb)에서 `Figure`, `Axes`,
`Axis`, `Artist`의 관계를 확인한다. `figsize`, `dpi`, 배경, layout, `add_subplot`,
`plt.subplots`, 축 설정과 `savefig`를 연습한다. 다음 notebook에서 pandas가 반환하는
Axes를 직접 다루기 위한 준비 단계다.

### 2-5. pandas와 Matplotlib 연결

[pandas와 Matplotlib 연결](05_pandas+visualization.ipynb)에서 Series/DataFrame
plot이 반환하는 Axes, 미리 만든 Axes를 `ax=`로 전달하는 패턴, pandas subplot의 반환
배열을 다룬다. line, bar, barh, hist, box, scatter, hexbin을 질문에 맞게 선택하고,
GroupBy·crosstab·rolling·resample 결과를 시각화한다. 정렬, 결측값, 공통 axis,
percentage tick, annotation, legend와 Artist style까지 chart 검토 흐름을 연결한다.

### 2-6. EDA 기초

[EDA 기초](06_eda_basics.ipynb)에서 population, sample, row grain과 prediction 시점을
정의하고 schema, target·feature 분포, 결측, 중복과 범위를 확인한다. Pearson·Spearman
correlation과 feature redundancy, split profile을 살펴보고 기술·추론·예측·인과
질문을 구분해 EDA finding을 기록한다.

### 2-7. Feature Engineering 기초

[Feature Engineering 기초](07_feature_engineering_basics.ipynb)에서 long-format 관측값을
patient-level feature로 집계하고 derived feature와 missing indicator를 만든다. Filter,
wrapper, embedded와 inspection을 구분하고 correlation, mutual information, 단변량
Logistic Regression, coefficient, tree importance와 permutation importance를 비교한다.
Leakage, redundancy, stability와 feature contract를 함께 검토한다.

### 2-8. Great Expectations 기초

[Great Expectations 기초](08_great_expectations_basics.ipynb)에서 in-memory pandas
DataFrame을 Data Source, Data Asset과 Batch Definition에 연결한다. Expectation을
개별 실행한 뒤 Expectation Suite, Validation Definition과 Checkpoint로 확장하고,
실패한 규칙의 statistics와 unexpected value를 읽는다.

### 2-9. DVC 기초

[DVC 기초](09_dvc_basics.ipynb)에서 임시 Git·DVC project를 만들고 `dvc add`,
`dvc stage add`, `dvc repro`, `dvc status`, `dvc dag`를 실행한다. `.dvc` pointer,
`dvc.yaml`, `params.yaml`, `dvc.lock`, cache와 remote의 역할을 구분한다.

### 2-10. scikit-learn 기초

[scikit-learn 기초](10_scikit-learn_basics.ipynb)에서 `X`와 `y`, stratified split,
estimator의 `fit`·`predict`·`predict_proba`를 익힌다. `ColumnTransformer`와
`Pipeline`으로 imputation, scaling, encoding과 classifier를 연결하고 metric,
cross-validation과 parameter search를 leakage 없이 수행한다.

### 2-11. MLflow 기초

[MLflow 기초](11_mlflow_basics.ipynb)에서 임시 local tracking backend를 구성한다.
Experiment와 Run에 parameter, metric, tag, dataset과 JSON artifact를 기록하고,
signature를 포함한 scikit-learn model을 log한 뒤 API로 조회하고 다시 load한다.

## 3. 학습 흐름

### 3-1. Python 객체에서 label이 있는 표로 확장

Python 객체가 mutable인지 확인한 뒤 Series, DataFrame, Index로 label이 있는 표를
구성한다. 현재 객체의 type, shape, dtype과 각 row를 식별하는 Index를 함께 확인한다.

### 3-2. label 규칙과 배열 규칙을 구분해 계산

현재 객체가 Series인지 DataFrame인지, 한 행이 무엇을 의미하는지, 어떤 Index가 행을
식별하는지 확인한다. 이후 같은 계산을 NumPy의 shape·위치 규칙과 pandas의 label
alignment 규칙으로 비교한다. raw 행은 분석 질문에 맞는 grain으로 집계하고, 집계표의
index, columns, 분모와 단위를 검토한다.

### 3-3. pandas plot 이후 Axes 후처리

pandas plot의 반환값을 보관하고 그 Axes에 Matplotlib 설정을 적용한다. 여러 chart가
필요하면 Figure와 Axes grid를 먼저 만들고 `ax=`로 전달해 layout 소유권을 분명히 한다.

### 3-4. EDA에서 Feature Engineering으로 연결

EDA에서 data grain, 분포, 결측과 feature 관계를 확인하고 finding을 가설과 위험으로
기록한다. Feature Engineering에서는 observation window 안의 candidate를 만들고 여러
association·importance 방법을 비교한다. 높은 점수 하나로 결정하지 않고 availability,
leakage, redundancy, stability와 feature contract를 함께 검토한다.

### 3-5. 검증에서 재현 가능한 artifact까지 연결

EDA에서 발견한 data invariant를 Great Expectations의 실행 가능한 규칙으로 옮긴다.
검증 결과와 data, pipeline output을 DVC revision으로 재현한 뒤 train data를
scikit-learn Pipeline에 전달한다. 실행 metadata와 model은 MLflow Run으로 추적하며,
Git revision, DVC lock digest, MLflow Run과 release manifest의 역할을 구분해 연결한다.

## 4. 실행 방법

VS Code에서 위 순서대로 열어 위에서 아래로 실행한다. 필요한 환경은 다음과 같다.

```bash
uv sync --all-packages --group notebook
```

## 5. 해석 범위

이 자료의 합성 데이터와 chart는 기초 개념과 API의 동작을 설명한다. 합성 data의
correlation, regression score와 importance는 실제 PhysioNet feature의 임상적 유효성을
뜻하지 않는다. Appendix의 feature screening은 train/CV와 validation 범위의 교육용
예제이며 canonical feature set, threshold 또는 V2 sealed test 결과를 변경하지 않는다.
실제 workflow에서는 versioned artifact, aggregation plan과 feature contract를 기준으로
결과를 해석한다.
