# 5장 QA 전략 Lab

5장은 앞 장의 데이터 품질, 모델 품질, serving, observability evidence를 release 승인/보류 판단으로 묶는 실습입니다.

## 실습 자료

| 구분 | 경로 | 역할 |
| --- | --- | --- |
| README | `labs/ch05_qa_strategy/README.md` | 5장 QA 전략 실습 목적, 실행 순서, QA 해석 |
| Notebook | `labs/ch05_qa_strategy/qa_strategy_lab.ipynb` | drift, score 분포, incident trace, release criteria 연결 |
| QA artifact script | `labs/ch05_qa_strategy/build_qa_artifacts.py` | drift report, release approval, checklist 생성 |

## 직접 실행 순서

```bash
uv run python labs/ch05_qa_strategy/build_qa_artifacts.py
```

같은 작업을 wrapper로 실행할 수도 있습니다.

```bash
uv run python scripts/course.py lab-qa-strategy
```


## 5-1. 입력 데이터 분포 변화 확인 [Lab]

5-1 Lab의 목표는 현재 운영 입력 샘플이 기준선(baseline)과 달라졌는지 확인하는 것입니다. 평균, 히스토그램(histogram), 결측/이상 비율을 함께 보고, current batch 입력 구성 변화가 점수(score)와 예측(prediction) 변화의 원인 후보가 될 수 있는지 판단합니다.

5-1의 판단 질문은 운영 이상 신호가 current batch 입력 구성 변화와 연결되는지입니다. 앞 장에서는 `high_risk` 비율, 평균 점수, 오류율(error rate), 지연 시간(latency)이 함께 변하는 운영 이상 신호를 확인했습니다. 5-1에서는 그 변화의 원인 후보 중 하나인 현재 배치의 입력 데이터 분포 변화를 먼저 확인합니다. 이 변화는 자연 시간 drift가 확정되었다는 뜻이 아니라, 이후 점수와 예측 분포 분석으로 연결해야 하는 case-mix shift 단서입니다.

이 Lab의 핵심은 current batch 입력 분포 변화를 점수와 예측 변화의 원인 후보로 남길지 판단하는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch05_qa_strategy/README.md` | current batch 입력 분포 변화의 의미와 QA 해석 확인 |
| Notebook | `labs/ch05_qa_strategy/qa_strategy_lab.ipynb` | 5장 Lab 흐름을 셀 단위로 실행 |
| CLI 스크립트 | `labs/ch05_qa_strategy/build_qa_artifacts.py` | 입력 분포 비교와 drift report 생성 |

## 5-1-1. 입력 분포란 무엇인가

입력 분포는 모델에 들어오는 특성(feature) 값들이 어떤 범위와 패턴으로 나타나는지를 의미합니다. 평균, 최솟값, 최댓값, 히스토그램, 결측 비율, 이상치 비율이 모두 입력 분포를 설명하는 정보입니다.

모델은 학습 데이터의 특성 분포를 기준으로 패턴을 배웁니다. 운영 환경에서 들어오는 특성 분포가 학습과 평가 때와 크게 달라지면 API는 정상 응답을 반환하더라도 점수와 예측 품질은 흔들릴 수 있습니다.

입력 구간 변화는 같은 모델과 임계값에서도 점수 분포(score distribution)를 이동시킬 수 있습니다. 예를 들어 기준 운영 샘플보다 현재 운영 샘플에서 `heart_rate`가 상대적으로 높고 `oxygen_saturation`이 낮은 행(row)이 더 많이 관측되었다고 하겠습니다. 모델은 같은 버전과 같은 임계값으로 응답하더라도 입력 구간이 달라지면 점수 분포가 이동할 수 있습니다.

QA 관점에서는 입력 분포 변화를 current batch case-mix shift의 초기 신호로 봅니다. `drift_report.md`라는 파일명은 비교 리포트의 이름일 뿐이며, 이 값만으로 자연 시간 drift나 모델 결함을 확정하지 않습니다.

## 5-1-2. Histogram 기반 분포 확인

실습 목표는 기준 요청 데이터와 현재 요청 데이터를 비교해 특성 분포가 바뀌었는지 확인하는 것입니다. 평균만 보면 놓칠 수 있는 변화를 히스토그램으로 함께 봅니다.

이 단계의 준비 데이터는 기준선과 현재 요청의 입력 구성을 비교하기 위한 근거입니다. 준비 데이터는 다음과 같습니다.

| 항목 | 파일 |
| --- | --- |
| 기준선 | `data/serving_requests_valid.csv` |
| 현재(current) | `data/serving_requests_current.csv` |
| 특성 목록 | `configs/validation/model_features.yaml` |
| 산출물 | `artifacts/reports/drift_report.md` |

문서에는 핵심 로직만 보여줍니다. 전체 코드는 `packages/ai-quality/src/ai_quality/qa_strategy/application/detect_input_shift.py`에 있습니다.

```python
def compare_input_distribution(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    feature_columns: list[str],
    bin_count: int = 5,
) -> list[FeatureDistributionComparison]:
    comparisons: list[FeatureDistributionComparison] = []

    for feature in feature_columns:
        baseline_values = _numeric_values(baseline, feature)
        current_values = _numeric_values(current, feature)
        baseline_mean = _mean(baseline_values)
        current_mean = _mean(current_values)
        denominator = abs(baseline_mean) if baseline_mean != 0 else 1.0
        mean_delta = current_mean - baseline_mean
        edges = _histogram_edges([*baseline_values, *current_values], bin_count)
        comparisons.append(
            FeatureDistributionComparison(
                feature=feature,
                baseline_mean=baseline_mean,
                current_mean=current_mean,
                mean_delta=mean_delta,
                mean_delta_ratio=mean_delta / denominator,
                histogram_bins=_histogram_labels(edges),
                baseline_histogram=_histogram_counts(baseline_values, edges),
                current_histogram=_histogram_counts(current_values, edges),
            )
        )

    return comparisons
```

이 실행은 입력 분포 변화 후보를 리포트와 표준 출력으로 남깁니다. 실행 코드는 다음과 같습니다.

```bash
uv run python labs/ch05_qa_strategy/build_qa_artifacts.py
```

이 출력에서 확인할 핵심은 어떤 특성이 기준선과 달라졌고 그 변화가 후속 점수/예측 분석으로 이어지는지입니다. 예상 결과는 다음과 같은 형태입니다. 마지막 줄에는 생성된 드리프트 리포트(drift report) 경로가 출력됩니다. 실제 경로는 실행 위치에 따라 절대 경로로 보일 수 있습니다.

```text
feature,baseline_mean,current_mean,delta,delta_ratio,histogram_distance,shifted
heart_rate,79.3417,89.8333,10.4917,0.1322,0.4833,True
respiratory_rate,15.8417,15.7083,-0.1333,-0.0084,0.0417,False
body_temperature,36.7583,36.7128,-0.0455,-0.0012,0.0833,False
oxygen_saturation,97.5631,96.0934,-1.4698,-0.0151,0.6000,True
systolic_blood_pressure,123.9000,123.5583,-0.3417,-0.0028,0.0667,False
diastolic_blood_pressure,80.3333,79.5583,-0.7750,-0.0096,0.1250,False
<repo>/artifacts/reports/drift_report.md
```

QA 해석에서는 값 하나가 달라졌는지보다 여러 특성이 같은 방향으로 움직이는지를 봅니다. `heart_rate`는 평균 변화가 크고, `oxygen_saturation`은 평균 변화율보다 히스토그램 변화가 큽니다. 이런 경우 입력 수집 경로, 전처리 코드, 샘플링 조건 변경을 함께 의심할 수 있습니다.

여기서 `shifted=True`는 “드리프트가 원인으로 확정되었다”는 뜻이 아닙니다. 해당 특성이 기준선과 달라졌으므로, 5-2에서 점수와 예측 분포 변화가 같은 방향으로 나타나는지 이어서 확인해야 한다는 뜻입니다.

실패 시 확인 포인트는 기준선/현재 파일 경로, 특성 목록, 숫자 변환 가능 여부입니다. 특성 이름이 데이터 컬럼과 맞지 않으면 비교가 되지 않습니다.

## 5-1-3. 평균값 변화 탐지

평균값 변화는 가장 이해하기 쉬운 drift 신호입니다. 기준 데이터의 평균과 현재 데이터의 평균을 비교해 얼마나 달라졌는지 봅니다. 하지만 평균만으로는 모든 분포 변화를 잡을 수 없습니다.

평균이 같아도 분포 모양이 달라지면 점수와 예측 품질은 흔들릴 수 있습니다. 예를 들어 기준선과 현재(current)의 평균은 같지만, 현재 데이터가 양쪽 극단으로 나뉘는 경우가 있습니다. 이런 경우 평균만 보면 변화가 없어 보이지만 히스토그램을 보면 분포가 크게 달라졌음을 알 수 있습니다.

| 확인 방식 | 장점 | 한계 |
| --- | --- | --- |
| 평균 비교 | 이해하기 쉽고 빠름 | 분포 모양 변화는 놓칠 가능 |
| 히스토그램 비교 | 분포 형태 변화를 볼 가능 | bin 설정에 따라 해석이 달라질 가능 |
| 결측/이상 비율 | 데이터 품질 변화 직접 확인 | score 영향 별도 확인 필요 |

QA는 평균 변화가 큰 특성을 발견하면 해당 특성이 모델 점수에 중요한 입력인지 확인해야 합니다. 중요 특성의 평균 변화는 예측 분포(prediction distribution) 변화로 이어질 가능성이 큽니다.

## 5-1-4. 입력 이상 징후 해석

입력 이상 징후는 단일 원인으로 단정하지 않습니다. 특성 평균 변화, 히스토그램 변화, 검증 실패(validation failure) 증가, 특정 출처(source)의 요청 증가가 함께 나타날 수 있습니다.

| 관측 | 원인 후보 |
| --- | --- |
| 여러 특성 평균이 동시에 이동 | 입력 출처(source) 변경, 샘플링 조건 변경 |
| 특정 특성만 극단적으로 이동 | 해당 특성 수집 오류 |
| 히스토그램 변화가 크고 평균 변화는 작음 | 분포 양극화 또는 특정 구간 증가 |
| 검증 실패도 함께 증가 | 스키마(schema) 변경 또는 클라이언트 페이로드(client payload) 오류 |

QA 보고에서는 “입력 변화 발생”이라고만 쓰지 말고, 현재 배치에서 어떤 특성이 어떤 방향으로 얼마나 바뀌었는지, 점수와 예측에 어떤 변화가 동반되었는지를 함께 기록해야 합니다.

## 5-2. 점수와 예측 분포 분석 [Lab]

5-2 Lab의 목표는 운영 요청의 점수(score) 분포와 예측(prediction) 분포를 함께 비교하는 것입니다. 점수는 임계값(threshold) 적용 전 모델 출력이고, 예측은 임계값 적용 후 최종 클래스(class)입니다. 두 값을 함께 봐야 입력 분포 변화, 모델 버전(model_version) 변경, 임계값 변경 후보를 구분할 수 있습니다.

5-1에서 `heart_rate`와 `oxygen_saturation`의 current batch 입력 분포 변화가 확인되었습니다. 5-2에서는 그 변화와 함께 평균 점수(score average)와 `high_risk` 예측 비율도 움직였는지 확인합니다. 입력이 바뀌었는데 점수와 예측이 그대로라면 영향이 제한적일 수 있고, 함께 움직였다면 입력 구성 변화가 중요한 원인 후보로 남습니다.

이 Lab의 핵심은 점수 분포와 예측 분포를 함께 읽어 입력 변화, 모델 변경, 임계값 변경 후보를 분리하는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch05_qa_strategy/README.md` | 점수와 예측 분포 변화의 의미와 QA 해석 확인 |
| Notebook | `labs/ch05_qa_strategy/qa_strategy_lab.ipynb` | 5장 Lab 흐름을 셀 단위로 실행 |
| CLI 산출물 생성 | `labs/ch05_qa_strategy/build_qa_artifacts.py` | 점수 평균, `high_risk` 비율 변화, 입력 구성 변화 리포트 생성 |

## 5-2-1. 점수 분포(score distribution) 이해

점수 분포는 모델이 운영 요청에 대해 어떤 점수를 내는지의 분포입니다. 점수는 임계값 적용 전 모델 출력이므로, 예측보다 먼저 변화를 보여줄 수 있습니다.

`score = 실제 확률`로 단정하면 안 됩니다. 점수는 모델 출력값이며, 임계값과 보정(calibration) 상태에 따라 해석이 달라집니다. 품질 관측에서는 점수 자체의 절대 의미보다 분포 변화와 임계값 영향에 집중합니다.

평균 점수(score average)가 증가했다면 입력 특성(feature)이 관심 클래스(Positive class) 쪽으로 이동했거나, 모델 버전이 바뀌었거나, 전처리 방식이 달라졌을 수 있습니다. 평균 점수가 낮아졌다면 반대 방향의 입력 변화나 결측값 처리를 의심할 수 있습니다.

## 5-2-2. 예측 분포(prediction distribution) 이해

예측 분포는 최종 예측 클래스의 비율입니다. 이번 사건처럼 `high_risk` 비율이 기준선(baseline)에서는 0.2167이었는데 현재(current)에서 0.4583이 되었다면 운영상 중요한 변화입니다.

예측 분포는 점수와 임계값의 결과입니다. 따라서 예측 비율만 보면 원인을 알 수 없습니다. 점수가 변했는지, 임계값이 바뀌었는지, 예측 클래스 값 기준이나 집계 기준이 바뀌었는지 함께 확인해야 합니다.

| 관측 조합 | 해석 후보 |
| --- | --- |
| 점수 증가, `high_risk` 비율 증가 | 입력 분포 변화, 모델 버전 변경 |
| 점수 변화 작음, `high_risk` 비율 증가 | 임계값 변경 가능성 |
| 점수 증가, `high_risk` 비율 변화 작음 | 임계값이 높거나 임계값 근처 샘플(sample)이 적음 |
| 검증 실패(validation failure) 증가 동반 | 입력 계약(contract) 문제를 먼저 확인 |

## 5-2-3. 특정 클래스 예측 급증 분석

실습 목표는 평균 점수(score average)와 `high_risk` 예측 비율 변화를 비교하는 것입니다.

이 단계의 준비 데이터는 정상/이상 예측 이벤트를 같은 기준으로 비교하기 위한 근거입니다. 준비 데이터는 앞 장에서 생성한 정상/이상 예측 이벤트(prediction event)입니다. 전체 코드는 `packages/ai-quality/src/ai_quality/qa_strategy/application/analyze_prediction_shift.py`에 있습니다.

```python
def compare_score_distribution(
    baseline_events: Sequence[PredictionEvent],
    current_events: Sequence[PredictionEvent],
) -> ScoreDistributionComparison:
    baseline = build_quality_snapshot(baseline_events)
    current = build_quality_snapshot(current_events)

    return ScoreDistributionComparison(
        baseline_average_score=baseline.average_score,
        current_average_score=current.average_score,
        average_score_delta=current.average_score - baseline.average_score,
        baseline_high_risk_rate=baseline.high_risk_rate,
        current_high_risk_rate=current.high_risk_rate,
        high_risk_rate_delta=current.high_risk_rate - baseline.high_risk_rate,
    )
```

이 실행에서 확인할 핵심은 평균 점수 변화와 `high_risk` 비율 변화가 같은 방향으로 움직였는지입니다. Notebook에서는 `labs/ch05_qa_strategy/qa_strategy_lab.ipynb`의 score/prediction distribution 셀을 실행합니다. 명령행에서 5장 QA 산출물을 다시 만들 때는 `uv run python labs/ch05_qa_strategy/build_qa_artifacts.py`를 사용합니다.

이 출력에서 확인할 핵심은 입력 구성 변화가 점수와 예측 변화의 원인 후보로 남을 만큼 동반되는지입니다. 예상 결과는 기준선과 현재(current)의 평균 점수, `high_risk` 비율 차이를 보여줍니다.

```text
baseline_average_score=0.5020
current_average_score=0.6402
average_score_delta=0.1382
baseline_high_risk_rate=0.2167
current_high_risk_rate=0.4583
high_risk_rate_delta=0.2417
```

QA는 이 값을 5-1 입력 분포 변화와 연결합니다. `heart_rate` 평균이 올라가고 `oxygen_saturation` 평균이 낮아진 상태에서 평균 점수와 `high_risk` 비율도 함께 증가했습니다. 따라서 current batch 입력 구성 변화는 중요한 원인 후보입니다. 다만 모델 버전, 임계값, 검증 실패를 함께 확인하기 전까지는 확정 원인으로 쓰지 않습니다.

실패 시 확인 포인트는 예측 이벤트(prediction event) 로그 생성 여부, 필드(field) 이름, 임계값 값입니다. 점수와 예측이 로그에 없으면 분포 분석을 할 수 없습니다.

## 5-2-4. 임계값 기준 FP/FN 변화 해석

임계값은 점수를 예측으로 바꾸는 기준입니다. 운영 중 임계값이 바뀌면 점수 분포가 그대로여도 예측 분포가 바뀔 수 있습니다.

QA는 임계값 근처 샘플에 주의해야 합니다. 점수가 0.49~0.51에 몰려 있다면 임계값을 조금만 바꿔도 예측이 크게 바뀔 수 있습니다. 이런 상황에서는 배포 전 임계값 변경 영향 분석이 필요합니다.

| 점수 위치 | QA 해석 |
| --- | --- |
| 임계값보다 충분히 낮음 | 임계값 변경에 덜 민감 |
| 임계값 근처 | 작은 설정 변경에도 예측이 바뀔 가능 |
| 임계값보다 충분히 높음 | Positive 예측이 안정적일 수 있음 |

이 내용은 2장의 임계값 분석과 연결됩니다. 배포 전 평가에서는 임계값별 FP/FN을 확인하고, 운영에서는 점수 분포와 예측 분포로 임계값 영향을 감시합니다.

## 5-3. 운영 이상 징후 탐지와 원인 추적 [Lab]

5-3 Lab의 목표는 5-1의 current batch 입력 구성 변화, 5-2의 점수와 예측 분포 변화, 4장의 운영 관측 신호를 하나의 원인 후보 표로 연결하는 것입니다. 이상 징후 분석은 하나의 지표를 보고 바로 원인을 단정하는 활동이 아니라, 후보를 줄여 가는 활동입니다.

이 Lab의 핵심은 입력, 점수, 운영 신호를 원인 후보와 owner가 있는 추적표로 바꾸는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch05_qa_strategy/README.md` | 이상 징후 분석 순서와 원인 후보 정리 방식 확인 |
| Notebook | `labs/ch05_qa_strategy/qa_strategy_lab.ipynb` | 5장 Lab 흐름을 셀 단위로 실행 |
| CLI 스크립트 | `labs/ch05_qa_strategy/build_qa_artifacts.py` | 입력, 점수, 운영 신호를 원인 후보로 연결 |

**분석 순서는 다음과 같습니다. 이 순서의 목적은 원인을 빠르게 하나로 정하는 것이 아니라, 확인할 후보를 누락하지 않는 것입니다.**

| 순서 | 확인할 것 | 원인 후보를 줄이는 방식 |
| --- | --- | --- |
| 1 | current batch 입력 구성 변화 | 특정 특성(feature) 변화가 점수(score) 변화와 함께 나타나는지 확인 |
| 2 | 점수와 예측(prediction) 분포 | 임계값(threshold) 전후 변화와 모델 출력 변화 분리 |
| 3 | 검증 실패(validation failure) | 잘못된 요청이 분포 분석에 섞였는지 확인 |
| 4 | 모델 버전(model_version)과 임계값 | 배포 설정 변경을 먼저 배제 |
| 5 | `request_id` 기반 로그 | 대표 요청을 찾아 실제 필드(field)와 응답을 확인 |
| 6 | 원인 후보 정리 | 데이터, 모델, 설정, 운영 환경으로 분리 |

## 5-3-1. 정상 상태와 이상 상태 비교

이상 징후는 기준선(baseline)과 비교해야 의미가 있습니다. 현재 오류율(error rate)이 5%라는 사실만으로는 심각한지 알기 어렵습니다. 평소 0.1%였다면 큰 문제이고, 평소 4.8%였다면 작은 변화일 수 있습니다.

정상 상태와 이상 상태를 비교할 때는 데이터, 모델 출력, 운영 지표를 함께 봅니다.

| 영역 | 기준선과 현재 비교 항목 |
| --- | --- |
| 입력 데이터 | 특성 평균, 히스토그램(histogram), 결측/이상 비율 |
| 모델 출력 | 평균 점수(average score), 예측 비율(prediction rate) |
| 운영 품질 | 오류율, 지연 시간(latency), 검증 실패 |
| 설정 | 모델 버전, 임계값 |

QA는 각 영역의 변화를 한 표에 모아 원인 후보를 좁힙니다. 한 지표만 보면 원인을 잘못 단정하기 쉽습니다.

## 5-3-2. 데이터 품질 문제와 지표(metric) 변화 연결

품질 이상은 보통 하나의 지표만으로 설명되지 않습니다. 입력 분포, 예측 분포, 오류율, 지연 시간, 검증 실패를 함께 보며 원인 후보를 좁혀야 합니다.

핵심 로직은 `packages/ai-quality/src/ai_quality/qa_strategy/application/trace_quality_issue.py`에 있습니다.

```python
def trace_quality_issue(
    feature_comparisons: list[FeatureDistributionComparison],
    score_comparison: ScoreDistributionComparison,
    quality_report: QualitySignalReport,
    current_events: Sequence[PredictionEvent] | None = None,
) -> IssueTraceReport:
    candidates: list[IssueCandidate] = []
    shifted_features = [item.feature for item in feature_comparisons if item.shifted]

    if shifted_features:
        candidates.append(
            IssueCandidate(
                category="input_case_mix_shift",
                evidence=f"shifted_features={', '.join(shifted_features)}",
                owner="Data Engineering",
                audit_reference="artifacts/reports/drift_report.md#input-distribution",
                next_action="최근 입력 출처와 전처리 변경을 확인합니다.",
            )
        )
```

이 실행은 후보 원인, owner, audit reference, 다음 확인 항목을 하나의 추적 리포트로 남깁니다. 실행 코드는 다음과 같습니다.

```bash
uv run python labs/ch05_qa_strategy/build_qa_artifacts.py
```

이 출력에서 확인할 핵심은 원인 후보가 데이터, 예측, 검증 실패, 지연 시간으로 분리되어 있는지입니다. 예상 출력은 다음과 같은 형태입니다.

```text
quality notes
- 오류율이 증가했습니다. 검증 실패를 확인합니다.
- 지연 시간이 증가했습니다. 서비스 부하나 의존성 지연을 확인합니다.
- 예측 분포가 high_risk 쪽으로 이동했습니다.
- 점수 분포가 높은 방향으로 이동했습니다.
score signal
average_score_delta=0.1382
high_risk_rate_delta=0.2417
issue candidates
- input_case_mix_shift: shifted_features=heart_rate, oxygen_saturation, owner=Data Engineering, audit_reference=artifacts/reports/drift_report.md#input-distribution
- prediction_shift: high_risk_rate_delta=0.2417, owner=ML Engineering, audit_reference=artifacts/reports/drift_report.md#score-and-prediction-distribution
- api_validation: error_rate_delta=0.0667, owner=Client Integration, audit_reference=request_id=current-0000, client_id=partner-feed-v2, source_system=upstream-partner-feed, failed_field=oxygen_saturation
- service_latency: latency_delta_ms=120.0, owner=Platform/MLOps, audit_reference=artifacts/grafana/ai_quality_overview_dashboard.json#average-latency
<repo>/artifacts/reports/quality_issue_trace.md
```

이 산출물은 최종 보고서에서 owner와 재평가 조건을 연결하는 근거입니다. 실제 경로는 실행 위치에 따라 절대 경로로 보일 수 있습니다.

| 파일 | 내용 |
| --- | --- |
| `artifacts/reports/quality_issue_trace.md` | 원인 후보, 근거, 담당 owner, audit reference, 다음 확인 항목 |

**QA 해석에서는 “모델 자체 문제”라고 바로 쓰기보다 근거를 나누어 적습니다.** 위 출력에서는 current batch 입력 구성 변화, 예측 분포 변화, API 검증 실패, 지연 시간 증가가 모두 후보로 남습니다. 후보마다 owner와 audit reference를 같이 남겨야 보고서가 “무엇이 이상하다”에서 끝나지 않고 “누가 어떤 근거를 확인해야 재평가할 수 있다”로 이어집니다.

| 항목 | 예시 |
| --- | --- |
| 증상 | `high_risk` 예측 비율 증가 |
| 근거 | 평균 점수 상승, 특정 특성 평균 변화 |
| 후보 원인 | current batch 입력 구성 변화, 예측 분포 변화, 검증 실패, 서비스 지연 |
| 담당 owner | `Data Engineering`, `ML Engineering`, `Client Integration`, `Platform/MLOps` |
| 감사 추적 | `request_id`, `client_id`, `source_system`, `failed_field` 또는 근거 리포트 경로 |
| 다음 조치 | 최근 데이터 수집 경로, 배포 설정, API 오류 로그 확인 |

## 5-3-3. 로그 기반 원인 후보 좁히기

로그는 지표에서 본 이상을 요청 단위로 확인하는 자료입니다. 대시보드(dashboard)에서 `high_risk` 비율이 증가했다면 해당 시간대 로그에서 `request_id`, `score`, `threshold`, `model_version`, `validation_failure`를 확인합니다.

| 로그 필드 | 확인 이유 |
| --- | --- |
| `request_id` | 개별 요청 추적 |
| `model_version` | 모델 변경 여부 |
| `threshold` | 운영 기준 변경 여부 |
| `score` | 임계값 이전 출력 |
| `prediction` | 최종 클래스(class) |
| `validation_failure` | 입력 계약(contract) 문제 |

원인 후보를 좁힐 때는 먼저 설정 변경을 배제합니다. 모델 버전과 임계값이 바뀌지 않았는데 점수와 예측 분포가 바뀌었다면 입력 분포 변화를 더 의심할 수 있습니다. 반대로 점수는 그대로인데 예측만 바뀌었다면 임계값, 예측 클래스 값 기준, 집계 기준을 확인해야 합니다.

## 5-3-4. 품질 이상 원인 후보 정리

품질 이상 원인 후보는 데이터, 모델, 설정, 운영 환경으로 나누어 정리합니다. 이 구분은 보고와 후속 조치에 필요합니다.

| 원인 영역 | 근거 | owner | 후속 조치 |
| --- | --- | --- | --- |
| 데이터 | 특성 분포 변화, 검증 실패 | `Data Engineering` | 입력 출처(source)와 전처리 확인 |
| 모델 | AUROC/PR-AUC 하락, 점수 구분력 저하 | `ML Engineering` | 모델 평가 재실행 |
| 설정 | 임계값, 모델 버전 불일치 | `Release Owner` | 배포 설정 확인 |
| 운영 | 오류율, 지연 시간 증가 | `Platform/MLOps` 또는 `Client Integration` | API와 인프라 상태 확인 |

**QA 보고서에는 확정 원인과 후보 원인을 구분해야 합니다.** 근거가 부족한 상태에서 원인을 단정하면 후속 조치가 잘못될 수 있습니다.

## 5-6. 배포 승인과 운영 전환 기준 [Core]

배포 승인 판단은 모델 지표(metric) 하나로 정하지 않습니다. 5-5에서 테스트 데이터 묶음을 나누었다면, 5-6에서는 그 결과를 데이터 조건, 모델 지표, API 계약(contract), 운영 관측 준비, 설정 일치성으로 묶어 승인 또는 보류 판단으로 정리합니다.

배포 승인은 “모델 지표가 기준을 넘었는가”보다 넓은 질문입니다. [Model Cards for Model Reporting](https://research.google/pubs/pub48120/)의 관점처럼 모델은 사용 목적(intended use), 평가 특성, 제한 사항을 함께 설명해야 합니다. QA의 승인/보류 판단도 마찬가지입니다. 어떤 데이터와 기준에서는 승인 가능한지, 어떤 제한이 있는지, 운영에서 어떤 신호를 봐야 하는지를 함께 남겨야 합니다.

승인 판단에 들어가는 입력은 다음과 같습니다. 이 표는 한 항목이라도 실패하면 무조건 같은 조치를 한다는 뜻이 아니라, 어떤 근거가 어떤 위험을 설명하는지 분리하기 위한 기준입니다.

| 승인 판단 입력 | 확인 내용 | 기준 미달 시 해석 |
| --- | --- | --- |
| 데이터 검증 결과 | 필수 컬럼, 라벨(label), 관심 클래스 표본 수(Positive support) | 평가 결과 자체를 제한적으로 해석 |
| 모델 지표 | 정밀도(Precision), 재현율(Recall), PR-AUC, FP/FN | 품질 기준 미달 또는 추가 임계값(threshold) 검토가 필요 |
| API 계약 | 입력 스키마(schema), 오류 응답, `request_id` | 운영 요청 처리와 추적이 불안정 |
| Live 배포 증거 | `/health`, `/predict`, Pod readiness, 응답 `model_version`, `threshold` | 실제 운영 환경 준비를 승인 근거로 쓰기 어려움 |
| 설정값 | 모델 버전(model_version), 임계값 | 평가 기준과 운영 기준이 달라질 가능 |
| 운영 신호 | 오류율(error rate), 지연 시간(latency), 검증 실패(validation failure) | 배포 후 서비스 품질 기준을 벗어날 가능성이 있음 |
| 운영 관측(observability) | 로그, 메트릭(metric), 대시보드(dashboard) | 문제 발생 시 원인 추적이 어려움 |

## 5-6-1. 지표 기준과 배포 가능/보류 판단

**배포 가능 여부는 지표, API 계약, 운영 신호를 함께 보고 판단합니다.** 정밀도와 재현율이 기준을 넘었더라도 오류율이 높거나 API 계약이 깨졌다면 운영 전환 위험이 남습니다. 반대로 어떤 지표가 기준에 미달했을 때도 실패 항목과 영향 범위를 기록해야 후속 조치를 정할 수 있습니다.

**보류 판단도 리스크가 없는 결정은 아닙니다.** 배포를 보류하면 개선 기능이 늦어지고 운영팀은 현재 버전을 더 오래 유지해야 할 수 있습니다. 따라서 QA 보고서는 “승인하면 생기는 리스크”와 “보류하면 생기는 리스크”를 나누어 쓰고, 어떤 조건이 충족되면 재평가할지 함께 남겨야 합니다.

핵심 로직은 `packages/ai-quality/src/ai_quality/qa_strategy/application/evaluate_release_approval.py`에 있습니다.

```python
def evaluate_release_approval(
    context: ReleaseContext,
    criteria: ApprovalCriteria,
) -> ApprovalDecision:
    notes: list[str] = []
    check_results = (
        ApprovalCheckResult(
            name="precision",
            observed=context.evaluation_report.metrics.precision,
            criterion=f">= {criteria.minimum_precision:.4f}",
            passed=context.evaluation_report.metrics.precision >= criteria.minimum_precision,
        ),
        ...
    )
    failed_checks = [result.name for result in check_results if not result.passed]

    unresolved_risks = (...)

    return ApprovalDecision(
        approved=not failed_checks and not unresolved_risks,
        failed_checks=tuple(failed_checks),
        notes=tuple(notes),
        check_results=check_results,
        unresolved_risks=tuple(unresolved_risks),
    )
```

승인 기준은 `configs/qa_strategy/approval_rules.yaml`에 둡니다. 이 파일은 최소 정밀도, 최소 재현율, 최대 오류율, 최대 평균 지연 시간(average latency)을 정의합니다. 운영 조직에서는 이 값을 서비스 위험도와 운영 정책에 맞게 조정해야 합니다.

이 실행은 작은 `release_candidate` 평가 결과와 운영 관측 이벤트를 함께 사용해 승인 판단 리포트를 만듭니다. 실행 환경은 저장소 루트의 로컬 shell입니다.

```bash
uv run python labs/ch05_qa_strategy/build_qa_artifacts.py
```

이 출력에서 확인할 핵심은 조건부 보류 판단이 어떤 실패 기준과 미검증 리스크에서 나왔는지입니다. 예상 출력은 다음과 같은 형태입니다.

```text
approved=False
recommendation=conditional_hold
failed_checks=('recall', 'error_rate')
precision=1.0000 criterion=>=0.6000 result=pass
recall=0.5926 criterion=>=0.6000 result=fail
error_rate=0.0667 criterion=<=0.0500 result=fail
prepared_api_contract=True result=pass
unresolved_risks=('live_deployment',)
- approve_now risk: 기준 미달 지표와 미검증 live evidence를 운영에 반영할 수 있음
- conditional_hold risk: 릴리스 지연과 현재 운영 버전 유지 부담이 생김
- 실패한 기준을 검토할 때까지 배포를 보류합니다.
<repo>/artifacts/reports/release_approval.md
```

이 산출물은 승인 여부, 실패 기준, owner, 재평가 조건을 보고서에 연결하는 근거입니다.

| 파일 | 내용 |
| --- | --- |
| `artifacts/reports/release_approval.md` | 승인 여부, 실패한 기준, 관측값, 기준값, 미검증 운영 리스크, 승인/보류 리스크, owner, 재평가 조건 |

**QA 해석에서는 `approved=False` 자체보다 실패 기준별 관측값을 먼저 읽습니다.** 위 예시는 Precision은 `1.0000`으로 최소 기준 `0.6000`을 통과했지만, Recall은 `0.5926`으로 최소 기준 `0.6000`에 근소하게 미달하고 error rate가 `0.0667`로 최대 기준 `0.0500`을 초과한 상황입니다. `prepared_api_contract=True`는 준비된 계약 확인이 통과했다는 의미이지 live deployment 검증이 끝났다는 의미가 아닙니다. 따라서 다음 조치는 모델만 재학습하는 것이 아니라 평가 데이터, 임계값, 오류 로그, 운영 이벤트, live smoke evidence를 함께 확인하는 쪽으로 잡아야 합니다.

보고서 문장은 다음처럼 양쪽 리스크를 모두 남깁니다.

| 판단 | 리스크 | 근거 | 재평가 조건 |
| --- | --- | --- | --- |
| 승인 | 기준 미달 상태가 운영에 반영되어 FN과 오류 요청이 증가할 수 있음 | `recall`, `error_rate` 실패 | 실패 기준 재측정과 검증 실패 원인 확인 |
| 보류 | 릴리스 지연과 현재 운영 버전 유지 부담이 생김 | `latency`, `prepared_api_contract`는 통과하지만 `live_deployment`는 미검증 | owner별 next action 완료 후 같은 기준으로 재평가 |
| 추가 확인 | 원인 단정 전 조사 시간이 필요함 | drift, prediction shift, api validation, latency 후보 존재 | `quality_issue_trace.md`의 owner와 audit reference 확인 |

## 5-6-2. API 계약과 설정값 확인

API 계약은 운영 요청이 어떤 형식으로 들어오고 어떤 응답을 받아야 하는지에 대한 약속입니다. 모델 지표가 기준을 만족해도 필수 필드(field)가 빠졌을 때 오류 응답이 불명확하거나, 응답에 `request_id`가 없다면 운영 전환을 승인하기 어렵습니다.

운영 서비스는 모델 파일만 배포되는 것이 아닙니다. API 스키마, 모델 버전, 임계값, 응답 필드, 로그 필드가 함께 배포됩니다. 평가에서 사용한 기준과 운영 설정이 다르면 같은 모델이라도 다른 예측(prediction) 분포를 만들 수 있습니다.

API 계약과 설정값은 다음처럼 확인합니다.

| 확인 항목 | 승인 기준 |
| --- | --- |
| 준비된 API 스키마 | 필수 필드와 오류 응답이 문서와 일치 |
| 모델 버전 | 승인된 모델 버전과 일치 |
| 임계값 | 평가에서 사용한 임계값 기준과 일치 |
| `request_id` | 로그 추적 가능 |
| Live 배포 | 실제 `/health`, `/predict`, Pod readiness, 응답 `model_version`, `threshold`가 확인됨 |

**QA 코멘트에는 “API 정상”처럼 넓게 쓰지 않습니다.** “필수 입력 누락 시 오류 응답 확인”, “응답에 `model_version`과 `threshold` 포함”, “로그에서 `request_id` 검색 가능”처럼 승인 기준을 관측 가능한 항목으로 남깁니다. 이번 로컬 실습에서는 live Kubernetes 요청을 필수로 실행하지 않으므로, live 증거가 없으면 “운영 배포 검증 완료”라고 쓰지 않고 `live_deployment=unverified`로 남깁니다.

## 5-6-3. 로그와 대시보드 기반 운영 준비 확인

운영 전환 전에는 로그와 대시보드가 준비되어 있어야 합니다. 문제가 발생한 뒤에 로그 필드를 추가하면 이미 발생한 요청은 추적하기 어렵습니다. 따라서 배포 승인 조건에는 관측 가능성도 포함되어야 합니다.

운영 준비는 대시보드가 예쁘게 보이는지가 아니라 품질 이상을 설명할 수 있는지를 확인하는 일입니다. 오류(error), 지연 시간, 검증 실패, 점수(score), 예측 분포가 함께 보이면 “API 문제인지, 입력 문제인지, 모델 출력 문제인지”를 더 빨리 나눌 수 있습니다.

| 준비 항목 | 확인 |
| --- | --- |
| 구조화 로그 | `request_id`, 점수, 임계값, 예측 기록 |
| 메트릭 | 요청(request), 오류(error), 지연 시간, 검증 실패 |
| 대시보드 | 점수 분포(score distribution)와 예측 분포(prediction distribution) 패널(panel) |
| 쿼리(query) | `request_id`, `trace_id` 조회 가능 |

운영 전환 기준에는 “문제가 생기면 볼 수 있다”가 아니라 “문제가 생겼을 때 어떤 요청과 설정을 추적할 수 있다”가 들어가야 합니다. 최소한 `request_id`, `model_version`, `threshold`, `score`, `prediction`, `validation_failure`, `latency_ms`는 연결되어야 합니다.

## 5-6-4. 배포 전후 품질 비교 기준

배포 전후 비교는 같은 기준으로 해야 합니다. 데이터셋(dataset), 특성(feature), 라벨 기준, 임계값이 다르면 지표 차이를 배포 효과로 단정할 수 없습니다.

비교 기준을 맞춘다는 것은 모든 값을 영원히 고정한다는 뜻이 아닙니다. 변경이 있다면 변경 사유와 영향 범위를 기록하고, 비교할 때 어떤 조건이 달라졌는지 드러내야 합니다. 그래야 품질 기준 미충족이 모델 변경 때문인지, 운영 입력 변화 때문인지, 설정 변경 때문인지 설명할 수 있습니다.

| 비교 항목 | 확인 |
| --- | --- |
| 전후 모델 버전 | 의도한 변경인지 |
| 임계값 | 동일한지 또는 변경 사유가 있는지 |
| 점수 분포 | 큰 이동이 있는지 |
| 예측 분포 | 특정 클래스(class) 급증이 있는지 |
| 오류(error)와 지연 시간 | 운영 안정성이 유지되는지 |

**배포 승인 문서의 결론은 “승인” 또는 “보류”라는 단어만으로 끝나면 부족합니다.** 어떤 기준을 통과했고, 어떤 기준을 실패했으며, 실패 항목을 해결하기 위해 어떤 확인이 필요한지 남겨야 5-8의 최종 AI QA 체크리스트로 이어질 수 있습니다.

## 5-8. AI QA 체크리스트 정리 [Lab]

5-8 Lab의 목표는 앞에서 만든 입력 구성 변화 리포트(`drift_report.md`), 예측 변화 리포트(prediction shift report), 원인 후보, 승인/조건부 보류 판단을 최종 QA 체크리스트와 release gate 문서로 묶는 것입니다. 체크리스트는 외우는 목록이 아니라, 품질 판단의 근거, 차단 상태, 다음 조치를 남기는 실무 산출물입니다.

**이 Lab에서는 새 분석을 많이 추가하지 않습니다.** 5-1부터 5-6까지 만든 산출물을 다시 연결해 “무엇을 확인했고, 어떤 근거가 있으며, 다음에 무엇을 해야 하는가”를 한 장으로 정리합니다.

이 Lab의 핵심은 앞 단계 evidence path를 조건부 보류와 재평가 조건이 있는 release gate 산출물로 묶는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch05_qa_strategy/README.md` | 최종 체크리스트 구성과 QA 코멘트 예시 확인 |
| Notebook | `labs/ch05_qa_strategy/qa_strategy_lab.ipynb` | 5장 Lab 흐름을 셀 단위로 실행 |
| CLI 스크립트 | `labs/ch05_qa_strategy/build_qa_artifacts.py` | 체크리스트 템플릿과 이번 사건 제출용 `ai_qa_checklist.md` 생성 |

실습 준비물은 다음과 같습니다. 앞 단계 산출물이 없으면 체크리스트는 형식만 남고 판단 근거가 비게 됩니다.

| 준비물 | 확인할 내용 |
| --- | --- |
| `drift_report.md` | current batch 입력 특성(feature) 분포 변화 |
| `label_basis_check.md` | 라벨 허용값, 라벨 매핑, 클래스별 표본 수 |
| 5-2 예측 변화 출력 | 점수(score) 평균과 `high_risk` 예측 비율 변화 |
| `quality_issue_trace.md` | 원인 후보, owner, audit reference, 다음 확인 항목 |
| `release_approval.md` | 승인 여부, 실패 기준, live deployment 미검증 리스크, 승인/보류 리스크, 재평가 조건 |
| `configs/qa_strategy/qa_checklist.yaml` | 반복 사용 체크리스트 항목 |

최종 체크리스트에는 data lineage도 함께 남깁니다. 여기서 lineage는 별도 플랫폼 화면이 아니라, **이번 판단에 사용한 데이터와 산출물이 어느 단계에서 파생되었는지 보여주는 근거 연결표**입니다. 이 연결표가 있어야 reviewer가 “test 결과인지, 운영 current batch 결과인지, validation 재현 결과인지”를 구분할 수 있습니다.

| 판단 단계 | 근거 데이터 | 근거 산출물 | 보고서에서 지켜야 할 경계 |
| --- | --- | --- | --- |
| 평가 가능성 확인 | `vital_signs_evaluation_baseline.csv` | `chapter_01_quality_report.md` | 1장 결론을 운영 입력 정상으로 확대하지 않음 |
| 모델 기준 평가 | `vital_signs_train.csv`, `vital_signs_test.csv` | `model_test_eval.json` | test는 선택된 모델과 threshold의 최종 모델 평가에만 사용 |
| 데이터 조건 변화 비교 | `vital_signs_valid_baseline.csv`, `vital_signs_valid_degraded.csv` | `validation_degradation_comparison.json` | 품질 저하 validation 비교를 운영 root cause 확정으로 쓰지 않음 |
| 운영 current 관측 | `serving_requests_current.csv`, `operational_current_events.jsonl` | `drift_report.md`, `quality_issue_trace.md` | current batch 입력 구성 변화와 검증 실패를 후보 근거로 표현 |
| 릴리스 판단 | `release_regression_cases.csv` | `release_approval.md`, `ai_qa_checklist.md` | 조건부 보류와 재평가 조건을 owner와 evidence path로 남김 |

이 표는 수강생이 최종 보고서에 붙일 수 있는 감사 추적(audit trail)의 최소 형태입니다. 예를 들어 `high_risk` 비율 증가를 쓸 때는 `model_test_eval.json`이 아니라 `drift_report.md`와 `operational_current_events.jsonl`을 근거로 삼아야 합니다. 반대로 모델 자체 성능 기준을 말할 때는 운영 로그가 아니라 `model_test_eval.json`과 approval rule을 확인해야 합니다.

## 5-8-1. 데이터 품질 체크리스트

데이터 품질 체크리스트는 모델 평가의 출발 조건을 확인합니다. 필수 컬럼(column), 결측값, 이상치, 라벨(label), 관심 클래스 표본 수(Positive support), 클래스(class) 비율, 파생 특성을 봅니다.

이 항목은 1장과 2장에서 다룬 데이터 품질 확인을 5장의 운영 판단으로 다시 가져오는 역할을 합니다. 예를 들어 `oxygen_saturation` 분포가 기준선(baseline)과 달라졌다면, 체크리스트에는 “확인 완료”만 표시하지 않고 어떤 리포트에서 어떤 변화가 보였는지 함께 남겨야 합니다.

데이터 품질 체크리스트는 다음 질문으로 해석합니다.

| 확인 항목 | QA 해석 |
| --- | --- |
| 필수 컬럼(column) 존재 | 평가와 서빙 입력 조건이 유지되는가 |
| 라벨 허용값 | `high_risk`, `low_risk` 기준이 유지되는가 |
| 관심 클래스 표본 수 | 재현율(Recall)과 FN 해석이 가능한가 |
| 분포 변화 | 회귀 테스트나 승인 판단에 제한 사항을 남겨야 하는가 |

**체크리스트는 단순 확인 목록이 아니라 의사결정 도구입니다.** 항목을 모두 채운 뒤에도 승인, 보류, 추가 확인 중 어떤 판단으로 이어지는지 설명하지 못하면 실무 산출물로 부족합니다.

## 5-8-2. 모델 품질 체크리스트

모델 품질 체크리스트는 정확도(Accuracy) 하나로 끝나지 않습니다. 정밀도(Precision), 재현율, 혼동 행렬(Confusion Matrix), FP/FN, PR-AUC, 임계값(threshold) 기준을 함께 확인합니다.

이 항목은 2장과 5-4의 회귀 테스트 기준을 연결합니다. 지표(metric)가 기준을 만족했는지뿐 아니라 어떤 데이터셋(dataset), 어떤 임계값, 어떤 모델 버전(model_version)에서 계산했는지를 남겨야 합니다.

모델 품질 항목은 다음처럼 읽습니다.

| 확인 항목 | QA 해석 |
| --- | --- |
| 정밀도와 재현율 | FP/FN 균형이 서비스 기준에 맞는가 |
| 혼동 행렬 | 어떤 오류 유형이 늘었는가 |
| PR-AUC | 클래스 불균형에서 관심 클래스 구분력이 유지되는가 |
| 임계값 영향 | 운영 기준 변경으로 예측(prediction)이 바뀌었는가 |

## 5-8-3. 임계값과 설정값 체크리스트

임계값과 설정값 체크리스트는 평가 기준과 운영 기준이 일치하는지 확인합니다. `model_version`, `MODEL_THRESHOLD`, 특성 목록, 예측 클래스 값 기준을 함께 봅니다.

설정값은 코드 변경이 없어도 운영 품질을 바꿀 수 있습니다. 같은 점수라도 임계값이 달라지면 예측이 바뀌고, 같은 API라도 모델 버전이 다르면 점수 분포가 달라질 수 있습니다.

QA는 설정 항목을 다음처럼 확인합니다.

| 확인 항목 | QA 해석 |
| --- | --- |
| `model_version` | 평가한 모델과 배포된 모델이 같은가 |
| `MODEL_THRESHOLD` | 평가 리포트와 운영 설정의 임계값이 같은가 |
| 특성 목록 | 학습, 평가, 서빙 입력이 일치하는가 |
| 예측 클래스 값 기준 | `high_risk`, `low_risk` 기준이 유지되는가 |

## 5-8-4. 운영 품질 체크리스트

운영 품질 체크리스트는 오류율(error rate), 지연 시간(latency), 검증 실패(validation failure), 요청 수(request count)를 포함합니다. 운영 신호는 모델 지표와 별도로 확인해야 합니다.

운영 지표가 기준을 벗어나면 모델 지표가 기준을 충족해도 서비스 품질은 낮을 수 있습니다. 예를 들어 오류율이 증가했는데 재현율만 높아졌다고 배포를 승인하면, 실제 사용자 요청은 실패하거나 늦게 응답할 수 있습니다.

운영 품질 항목은 다음처럼 해석합니다.

| 확인 항목 | QA 해석 |
| --- | --- |
| 오류율 | API 실패나 검증 실패가 증가했는가 |
| 지연 시간 | 응답 품질이 서비스 기준을 만족하는가 |
| 검증 실패 | 입력 계약(contract)이 깨지고 있는가 |
| 요청 수(request count) | 비교 기간의 트래픽(traffic)이 유사한가 |

## 5-8-5. Observability 체크리스트

운영 관측(observability) 체크리스트는 로그와 대시보드(dashboard)가 문제 분석에 충분한 정보를 제공하는지 확인합니다. `request_id`, `trace_id`, `score`, `threshold`, `prediction`, `model_version`이 핵심입니다.

관측 항목은 장애 이후에 추가하면 늦습니다. 문제가 발생했을 때 특정 요청을 찾고, 그 요청의 입력, 모델 버전, 점수, 임계값, 예측, 검증 실패 여부를 연결할 수 있어야 합니다.

관측 체크리스트는 다음처럼 해석합니다.

| 확인 항목 | QA 해석 |
| --- | --- |
| `request_id`, `trace_id` | 요청 단위 추적 가능 |
| `score`, `prediction` | 모델 출력과 최종 예측 연결 |
| `model_version`, `threshold` | 설정 변경 영향 추적 |
| 대시보드 | 오류, 지연 시간, 점수와 예측 분포 확인 |

## 5-8-6. 이상 징후 발견 시 보고 항목

이상 징후 보고에는 증상, 근거, 영향 범위, 원인 후보, 다음 조치가 포함되어야 합니다. 단정할 수 없는 내용은 후보로 표현합니다.

**보고 문장은 원인을 단정하는 한 줄 평가로 쓰지 않습니다.** “`high_risk` 비율 증가와 평균 점수 상승이 함께 보이며, `heart_rate` 평균 변화가 current batch에서 동반되어 입력 구성 변화를 우선 확인합니다”처럼 근거와 후보를 함께 남깁니다.

| 보고 항목 | 예시 |
| --- | --- |
| 증상 | `high_risk` 비율 증가 |
| 근거 | 평균 점수 상승, `heart_rate` 평균 증가 |
| 영향 범위 | 특정 시간대 요청 120건 |
| 원인 후보 | current batch 입력 구성 변화, 임계값 설정 확인 필요 |
| 다음 조치 | 데이터 수집 경로와 배포 설정 확인 |

보고 항목의 목적은 책임을 바로 정하는 것이 아니라 다음 확인 순서를 명확히 하는 것입니다. 확정 원인과 후보 원인을 구분해야 잘못된 후속 조치를 줄일 수 있습니다.

## 5-8-7. AI QA 전체 흐름 정리

핵심 로직은 `packages/ai-quality/src/ai_quality/qa_strategy/application/build_qa_checklist.py`에 있습니다. 설정 파일의 섹션과 항목을 읽어 체크리스트 산출물로 바꾸는 단순한 구조입니다.

```python
def build_qa_checklist(config: dict[str, Any]) -> QAChecklist:
    items: list[QAChecklistItem] = []
    for section, texts in config["sections"].items():
        for text in texts:
            items.append(
                QAChecklistItem(
                    section=str(section),
                    text=str(text),
                )
            )

    return QAChecklist(items=tuple(items))
```

이 실행은 최종 체크리스트와 release gate 제출본을 같은 evidence path 기준으로 생성합니다. 실행 환경은 저장소 루트의 로컬 shell이며, 실행 코드는 다음과 같습니다.

```bash
uv run python labs/ch05_qa_strategy/build_qa_artifacts.py
```

이 출력에서 확인할 핵심은 라벨 기준, 승인 판단, 체크리스트 템플릿, 제출용 점검본이 모두 생성되었는지입니다. 예상 출력은 다음과 같은 형태입니다.

```text
label_basis=<repo>/artifacts/reports/label_basis_check.md
release_approval=<repo>/artifacts/reports/release_approval.md
qa_checklist_template=<repo>/artifacts/reports/ai_qa_checklist_template.md
qa_checklist=<repo>/artifacts/reports/ai_qa_checklist.md
```

이 산출물들은 최종 보고서의 판단, evidence path, owner, next action을 뒷받침합니다.

| 파일 | 내용 |
| --- | --- |
| `artifacts/reports/ai_qa_checklist_template.md` | 데이터 품질, 모델 품질, 서빙 품질, 운영 관측, 이상 징후 보고 체크리스트 템플릿 |
| `artifacts/reports/ai_qa_checklist.md` | 이번 사건 제출용 점검본, 항목별 상태, 근거, QA 코멘트, 담당, 다음 조치 |
| `artifacts/reports/label_basis_check.md` | `high_risk`, `low_risk` 허용값과 표본 수, invalid/missing count |

**`ai_qa_checklist_template.md`는 반복 점검 템플릿이고, `ai_qa_checklist.md`는 이번 사건에 값을 채운 제출용 sign-off입니다.** 제출용 파일은 체크박스만 보여주지 않고 `pass`, `fail`, `unverified`, `hold` 같은 상태와 evidence path, 담당자, 다음 조치를 함께 남깁니다. 따라서 수강생은 최종 보고서에 아래 내용을 체크리스트 행으로 연결해 제출합니다.

| 보고 항목 | 이번 실습에서 남길 내용 |
| --- | --- |
| 최종 판단 | `recommendation=conditional_hold`, `approved=False`이므로 조건부 보류와 재평가 필요 |
| 실패 기준 | `recall=0.5926`, `error_rate=0.0667` |
| 라벨 기준 | `label_basis_check.md`에서 `invalid_count=0`, `missing_count=0`, `high_risk=37`, `low_risk=33` |
| 미검증 리스크 | `release_approval.md`에서 `live_deployment=unverified` |
| 확인 owner | `Data Engineering`, `ML Engineering`, `Client Integration`, `Platform/MLOps`, `QA Lead`, `Release Owner` |
| 감사 추적 | `quality_issue_trace.md`의 audit reference와 검증 실패 대표 요청 |
| 재평가 조건 | owner별 next action 완료 후 같은 approval rule로 재실행 |

AI QA 체크리스트의 마무리 기준은 다음과 같습니다.

| 완료 조건 | 확인 |
| --- | --- |
| 입력 분포 변화 확인 | `drift_report.md` 생성 |
| 라벨 기준 확인 | `label_basis_check.md` 생성 |
| 점수와 예측 변화 확인 | 5-2 출력 확인 |
| 원인 후보 추적 | `quality_issue_trace.md` 생성 |
| 승인/보류 판단 | `release_approval.md` 생성 |
| 체크리스트 템플릿 | `ai_qa_checklist_template.md` 생성 |
| 제출용 점검본 | `ai_qa_checklist.md`에서 `릴리스 준비 상태=blocked`, `status=hold`, `live_deployment=unverified`, owner와 next action 확인 |

실패 시에는 먼저 `configs/qa_strategy/qa_checklist.yaml` 문법을 확인합니다. 체크리스트 항목 수가 문서와 다르면 설정 파일이 변경되었는지 확인하고, 산출물 파일이 생성되지 않으면 `artifacts/reports/` 경로 쓰기 권한과 실행 위치를 확인합니다.

**AI QA 전략의 결론은 모델 지표 하나로 끝나지 않는다는 점입니다.** 데이터 분포, 점수, 예측, 임계값, API 계약(contract), 오류율, 지연 시간, 로그 추적 가능성을 함께 보고, 근거 기반으로 승인/보류와 후속 조치를 판단해야 합니다.
