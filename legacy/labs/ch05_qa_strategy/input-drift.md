# 5-1. 입력 데이터 분포 변화 확인 [Lab]

5-1 Lab의 목표는 현재 운영 입력 샘플이 기준선(baseline)과 달라졌는지 확인하는 것입니다. 평균, 히스토그램(histogram), 결측/이상 비율을 함께 보고, current batch 입력 구성 변화가 점수(score)와 예측(prediction) 변화의 원인 후보가 될 수 있는지 판단합니다.

5-1의 판단 질문은 운영 이상 신호가 current batch 입력 구성 변화와 연결되는지입니다. 앞 장에서는 `high_risk` 비율, 평균 점수, 오류율(error rate), 지연 시간(latency)이 함께 변하는 운영 이상 신호를 확인했습니다. 5-1에서는 그 변화의 원인 후보 중 하나인 현재 배치의 입력 데이터 분포 변화를 먼저 확인합니다. 이 변화는 자연 시간 drift가 확정되었다는 뜻이 아니라, 이후 점수와 예측 분포 분석으로 연결해야 하는 case-mix shift 단서입니다.

이 Lab의 핵심은 current batch 입력 분포 변화를 점수와 예측 변화의 원인 후보로 남길지 판단하는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/05_qa_strategy/input-drift.md` | current batch 입력 분포 변화의 의미와 QA 해석 확인 |
| 초급 Notebook | `labs/ch05_qa_strategy/01_collect_release_evidence.ipynb` | 입력 분포 변화와 입력 구성 변화 리포트 기초값 확인 |
| Lite Notebook | `jupyterlite/files/05_qa_strategy/01_collect_release_evidence.ipynb` | 브라우저에서 입력 분포 변화 확인 |
| 참고 Notebook | `labs/ch05_qa_strategy/03_qa_strategy_lab.ipynb` | 전체 5장 흐름을 한 번에 다시 볼 때 사용 |
| CLI 스크립트 | `labs/ch05_qa_strategy/04_build_qa_artifacts.py` | 입력 분포 비교와 입력 구성 변화 리포트 생성 |

!!! note "브라우저 실습"
    설치 없이 확인하려면 <a href="../../jupyterlite/lab/index.html?path=05_qa_strategy/01_collect_release_evidence.ipynb">JupyterLite에서 릴리스 근거 모으기</a>를 엽니다. 이 경로는 current batch 입력 구성 변화와 prepared report를 빠르게 확인하는 보조 실행 경로입니다.

## 5-1-1. 입력 분포란 무엇인가

입력 분포는 모델에 들어오는 특성(feature) 값들이 어떤 범위와 패턴으로 나타나는지를 의미합니다. 평균, 최솟값, 최댓값, 히스토그램, 결측 비율, 이상치 비율이 모두 입력 분포를 설명하는 정보입니다.

모델은 학습 데이터의 특성 분포를 기준으로 패턴을 배웁니다. 운영 환경에서 들어오는 특성 분포가 학습과 평가 때와 크게 달라지면 API는 정상 응답을 반환하더라도 점수와 예측 품질은 흔들릴 수 있습니다.

입력 구간 변화는 같은 모델과 임계값에서도 점수 분포(score distribution)를 이동시킬 수 있습니다. 예를 들어 기준 운영 샘플보다 현재 운영 샘플에서 `heart_rate`가 상대적으로 높고 `oxygen_saturation`이 낮은 행(row)이 더 많이 관측되었다고 하겠습니다. 모델은 같은 버전과 같은 임계값으로 응답하더라도 입력 구간이 달라지면 점수 분포가 이동할 수 있습니다.

QA 관점에서는 입력 분포 변화를 current batch case-mix shift의 초기 신호로 봅니다. `drift_report.md`라는 파일명은 비교 리포트의 이름일 뿐이며, 이 값만으로 자연 시간 drift나 모델 결함을 확정하지 않습니다.

Reference와 current를 어떻게 잡았는지가 drift 해석의 출발점입니다. [Evidently의 data drift 설명](https://www.evidentlyai.com/ml-in-production/data-drift)은 입력 feature 분포 변화를 기준 데이터와 현재 데이터의 비교로 봅니다. 이 과정에서는 `data/serving_requests_valid.csv`를 reference, `data/serving_requests_current.csv`를 current batch로 둡니다. 따라서 보고서에는 “운영 전체 drift 확정”이 아니라 “이번 current batch가 reference와 다르다”는 범위로 써야 합니다.

| 비교 기준 | 이 과정의 사용 | 보고서 표현 |
| --- | --- | --- |
| Reference dataset | `data/serving_requests_valid.csv` | 기준 운영 입력 분포 |
| Current dataset | `data/serving_requests_current.csv` | 이번 이상 신호 구간의 current batch |
| 비교 feature | `configs/validation/model_features.yaml` | 모델 입력 feature 기준 |
| 비교 목적 | 입력 변화가 score/prediction 변화 후보인지 확인 | 원인 후보 유지 또는 약화 |

Drift 확인 방법은 하나만 쓰지 않습니다. 초보자는 p-value나 거리 값 하나를 결론처럼 쓰기 쉽지만, 운영 QA에서는 먼저 데이터 품질 문제가 아닌지 확인하고, 그 다음 분포 비교를 통해 후속 조사 우선순위를 정합니다.

| 확인 방식 | 이 과정의 위치 | 말할 수 있는 것 | 말하면 안 되는 것 |
| --- | --- | --- | --- |
| 결측/범위/타입 확인 | 1장, 2장, 4장 validation failure | 입력 계약이 깨졌는지 | 모델 성능 저하 확정 |
| 평균 비교 | 5-1 `mean_delta` | feature 중심이 이동했는지 | 분포 모양 전체 설명 |
| Histogram 비교 | 5-1 bucket count | 특정 구간 요청이 늘었는지 | 자연 drift 원인 확정 |
| 통계 검정/거리 지표 | Mention | 자동 감지 기준 후보 | 실무 영향 크기 확정 |
| score/prediction 비교 | 5-2 | 입력 변화와 출력 변화가 동반되는지 | label 기반 품질 저하 확정 |

Grafana의 분포 화면과 5장 입력 구성 변화 리포트는 역할이 다릅니다. Grafana는 운영 metric이 계속 들어오는 상황에서 bucket별 count가 어떻게 바뀌는지 빠르게 보는 화면입니다. 반면 `drift_report.md`는 raw data를 기준으로 평균, histogram distance, feature별 표를 남기는 분석 산출물입니다. Evidently식 KDE나 density overlay처럼 부드러운 분포 그림이 필요하면 dashboard에서 즉석 계산하기보다 raw data 기반 리포트 산출물로 생성하는 편이 더 명확합니다.

| 위치 | 사용하는 데이터 | 적합한 질문 | 제한 |
| --- | --- | --- | --- |
| Grafana dashboard | Prometheus bucket/count metric | 지금 운영 신호가 어느 bucket에서 움직이는가 | KDE 자동 계산에는 부적합 |
| `drift_report.md` | 기준/current raw CSV | 어떤 feature가 얼마나 달라졌는가 | 실시간 streaming 화면은 아님 |
| 추가 density plot artifact | raw value로 계산한 x/y density | reference/current 모양이 어떻게 겹치거나 이동했는가 | 별도 계산 코드와 이미지 산출물 필요 |

## 5-1-2. Histogram 기반 분포 확인

실습 목표는 기준 요청 데이터와 현재 요청 데이터를 비교해 특성 분포가 바뀌었는지 확인하는 것입니다. 평균만 보면 놓칠 수 있는 변화를 히스토그램으로 함께 봅니다.

이 단계의 준비 데이터는 기준선과 현재 요청의 입력 구성을 비교하기 위한 근거입니다. 준비 데이터는 다음과 같습니다.

| 항목 | 파일 |
| --- | --- |
| 기준선 | `data/serving_requests_valid.csv` |
| 현재(current) | `data/serving_requests_current.csv` |
| 특성 목록 | `configs/validation/model_features.yaml` |
| 산출물 | `artifacts/reports/drift_report.md` |

입력 분포 비교의 핵심 로직은 `packages/ai-quality/src/ai_quality/qa_strategy/application/detect_input_shift.py`에 있습니다. 문서에서는 구현 코드를 다시 옮겨 적기보다, Notebook과 `artifacts/reports/drift_report.md`에서 어떤 값을 확인해야 하는지에 집중합니다. 로컬에서 재생성할 때는 `labs/ch05_qa_strategy/04_build_qa_artifacts.py`를 사용합니다.

이 출력에서 확인할 핵심은 어떤 특성이 기준선과 달라졌고 그 변화가 후속 점수/예측 분석으로 이어지는지입니다.

| feature | baseline mean | current mean | delta | histogram distance | shifted |
| --- | --- | --- | --- | --- | --- |
| `heart_rate` | `79.3417` | `89.8333` | `10.4917` | `0.4833` | `True` |
| `respiratory_rate` | `15.8417` | `15.7083` | `-0.1333` | `0.0417` | `False` |
| `body_temperature` | `36.7583` | `36.7128` | `-0.0455` | `0.0833` | `False` |
| `oxygen_saturation` | `97.5631` | `96.0934` | `-1.4698` | `0.6000` | `True` |
| `systolic_blood_pressure` | `123.9000` | `123.5583` | `-0.3417` | `0.0667` | `False` |
| `diastolic_blood_pressure` | `80.3333` | `79.5583` | `-0.7750` | `0.1250` | `False` |

QA 해석에서는 값 하나가 달라졌는지보다 여러 특성이 같은 방향으로 움직이는지를 봅니다. `heart_rate`는 평균 변화가 크고, `oxygen_saturation`은 평균 변화율보다 히스토그램 변화가 큽니다. 이런 경우 입력 수집 경로, 전처리 코드, 샘플링 조건 변경을 함께 의심할 수 있습니다.

여기서 `shifted=True`는 “드리프트가 원인으로 확정되었다”는 뜻이 아닙니다. 해당 특성이 기준선과 달라졌으므로, 5-2에서 점수와 예측 분포 변화가 같은 방향으로 나타나는지 이어서 확인해야 한다는 뜻입니다.

실무 영향은 감지 여부와 별도로 판단합니다. 작은 차이도 표본이 커지면 통계적으로는 유의하게 보일 수 있고, 큰 평균 변화라도 모델 점수와 예측이 안정적이면 즉시 운영 차단 사유가 아닐 수 있습니다. 이번 과정에서는 통계 검정을 Core로 다루지 않고, 평균 변화, histogram 변화, score/prediction 변화, validation failure를 묶어 원인 후보의 강도를 판단합니다.

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
