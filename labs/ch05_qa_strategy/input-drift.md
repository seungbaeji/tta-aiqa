# 5-1. 입력 데이터 분포 변화 확인 [Lab]

5-1 Lab의 목표는 현재 운영 입력 샘플이 기준선(baseline)과 달라졌는지 확인하는 것입니다. 평균, 히스토그램(histogram), 결측/이상 비율을 함께 보고, current batch 입력 구성 변화가 점수(score)와 예측(prediction) 변화의 원인 후보가 될 수 있는지 판단합니다.

5-1의 판단 질문은 운영 이상 신호가 current batch 입력 구성 변화와 연결되는지입니다. 앞 장에서는 `high_risk` 비율, 평균 점수, 오류율(error rate), 지연 시간(latency)이 함께 변하는 운영 이상 신호를 확인했습니다. 5-1에서는 그 변화의 원인 후보 중 하나인 현재 배치의 입력 데이터 분포 변화를 먼저 확인합니다. 이 변화는 자연 시간 drift가 확정되었다는 뜻이 아니라, 이후 점수와 예측 분포 분석으로 연결해야 하는 case-mix shift 단서입니다.

이 Lab의 핵심은 current batch 입력 분포 변화를 점수와 예측 변화의 원인 후보로 남길지 판단하는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/05_qa_strategy/input-drift.md` | current batch 입력 분포 변화의 의미와 QA 해석 확인 |
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
uv run --group lab python labs/ch05_qa_strategy/build_qa_artifacts.py
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
