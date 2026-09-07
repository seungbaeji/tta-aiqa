# 부록: 막힌 개념을 찾아보는 실습

## 1. 이용 방법

이 부록은 13개 노트북을 처음부터 차례대로 듣는 선행 과정이 아닙니다. 본편
실습에서 막힌 개념에 필요한 부분만 골라 확인하는 참고 경로입니다.

1. 지금 막힌 질문을 아래 표에서 찾습니다.
2. 해당 노트북의 목표와 필요한 부분만 실행합니다.
3. 마지막 검사 셀을 통과하면 본편 실습으로 돌아갑니다.

각 노트북은 작은 합성 데이터와 임시 저장 공간을 사용합니다. 수업의 공식 DVC
데이터, 모델 묶음이나 외부 서비스를 바꾸지 않습니다.

## 2. 질문별 선택 경로

| 지금 막힌 질문 | 열어 볼 노트북 | 확인할 핵심 |
| --- | --- | --- |
| Python 객체를 복사했는데 원본도 바뀌는 이유는 무엇인가요? | [01 Python 기초](01_python_basics.ipynb) | 객체 식별, 변경 가능성, 얕은 복사와 깊은 복사 |
| pandas가 행을 예상과 다르게 맞추는 이유는 무엇인가요? | [02 pandas 기초](02_pandas_basics.ipynb) | `Series`, `DataFrame`, `Index`, 레이블 정렬 |
| 배열의 축, 모양과 브로드캐스팅이 헷갈립니다. | [03 NumPy 기초](03_numpy_basics.ipynb) | `ndarray`, `shape`, `axis`, view와 copy |
| 그래프의 크기나 축을 어디서 바꿔야 하나요? | [04 Matplotlib 기초](04_matplotlib_basics.ipynb) | `Figure`, `Axes`, `Axis`, `Artist` |
| pandas 그래프를 만든 뒤 세부 모양을 바꾸고 싶습니다. | [05 pandas 시각화](05_pandas+visualization.ipynb) | 반환된 `Axes`, `ax=`, 여러 그래프 배치 |
| EDA에서 무엇을 먼저 확인해야 하나요? | [06 EDA 기초](06_eda_basics.ipynb) | 한 행의 의미, 분포, 결측, 중복, 질문 범위 |
| 특성을 만들고 고르는 방법을 구분하고 싶습니다. | [07 특성 공학 기초](07_feature_engineering_basics.ipynb) | 집계, 결측 표시, 누수, 중요도와 안정성 |
| 데이터 규칙을 자동 검사로 옮기고 싶습니다. | [08 Great Expectations 기초](08_great_expectations_basics.ipynb) | Expectation, Suite, Validation, Checkpoint |
| 데이터와 처리 결과를 재현하는 파일의 역할이 궁금합니다. | [09 DVC 기초](09_dvc_basics.ipynb) | `.dvc`, `dvc.yaml`, `params.yaml`, `dvc.lock` |
| 전처리와 모델을 한 흐름으로 묶고 싶습니다. | [10 scikit-learn 기초](10_scikit-learn_basics.ipynb) | `ColumnTransformer`, `Pipeline`, 교차검증 |
| 문제와 운영 판단에 맞는 평가 지표를 고르고 싶습니다. | [11 모델 지표 기초](11_metrics_basics.ipynb) | 기준선, 임계값, 혼동 행렬, 보정과 불확실성 |
| 클래스 불균형을 누수 없이 다루고 싶습니다. | [12 클래스 불균형 기초](12_class_imbalance_basics.ipynb) | 계층 분할, 가중치, 재표집, 운영 용량 |
| 실행 조건과 모델 파일을 함께 추적하고 싶습니다. | [13 MLflow 기초](13_mlflow_basics.ipynb) | Experiment, Run, 지표, 데이터와 산출물 |

## 3. 추천 조합

### 3-1. 1장 데이터 품질에서 막혔을 때

- 표 선택과 결측 처리: 02 pandas
- 배열과 pandas의 차이: 03 NumPy
- 탐색 순서: 06 EDA
- 자동 규칙: 08 Great Expectations

### 3-2. 2장 모델 품질에서 막혔을 때

- 특성 생성과 누수: 07 특성 공학
- 전처리와 평가 흐름: 10 scikit-learn
- 지표와 기준선: 11 모델 지표
- 불균형 자료의 평가와 학습: 12 클래스 불균형
- 실행 근거 조회: 13 MLflow

### 3-3. 그래프 해석에서 막혔을 때

- 그래프 객체 구조: 04 Matplotlib
- pandas 결과를 그래프로 연결하기: 05 pandas 시각화

### 3-4. 재현 파일의 역할이 헷갈릴 때

- Python 객체와 복사: 01 Python
- 데이터 처리 재현: 09 DVC
- 실행 기록과 모델 산출물: 13 MLflow

## 4. 노트북 안에서 보는 순서

각 노트북은 같은 구조를 사용합니다.

- `Goal`: 이번에 해결할 질문
- `Setup`: 본편을 오염시키지 않는 임시 환경
- `Steps`: 개념별 설명과 실행 예제
- `Checks`: 핵심 규약 확인
- `Next Steps`: 본편으로 돌아갈 때 적용할 내용
- `References`: 더 확인할 공식 자료

API 이름을 외우기보다 셀의 입력, 반환값과 객체가 어떻게 달라지는지 확인하세요.

## 5. 실행

저장소 루트에서 필요한 패키지를 준비합니다.

```bash
uv sync --all-packages --group dev --group notebook
```

VS Code에서 필요한 노트북 하나를 열어 위에서 아래로 실행합니다. 마지막에
`All appendix checks passed.`가 출력되는지 확인합니다.

## 6. 해석할 수 있는 범위

부록의 합성 데이터와 그래프는 개념과 API 동작을 설명하기 위한 예제입니다. 여기서
나온 상관계수, 회귀 점수나 특성 중요도를 실제 PhysioNet 특성의 임상적 유효성으로
해석하지 않습니다.

부록의 특성 검토는 학습/교차검증과 검증 자료를 사용하는 교육용 예제입니다. V2
공식 특성 집합, 임계값이나 공식 평가 결과를 바꾸지 않습니다. 본편에서는 버전이
지정된 산출물, 집계 계획과 모델 입력 규약을 기준으로 판단합니다.
