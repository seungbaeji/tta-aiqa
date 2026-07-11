# 5-2. 점수와 예측 분포 분석 [Lab]

5-2 Lab의 목표는 운영 요청의 점수(score) 분포와 예측(prediction) 분포를 함께 비교하는 것입니다. 점수는 임계값(threshold) 적용 전 모델 출력이고, 예측은 임계값 적용 후 최종 클래스(class)입니다. 두 값을 함께 봐야 입력 분포 변화, 모델 버전(model_version) 변경, 임계값 변경 후보를 구분할 수 있습니다.

5-1에서 `heart_rate`와 `oxygen_saturation`의 current batch 입력 분포 변화가 확인되었습니다. 5-2에서는 그 변화와 함께 평균 점수(score average)와 `high_risk` 예측 비율도 움직였는지 확인합니다. 입력이 바뀌었는데 점수와 예측이 그대로라면 영향이 제한적일 수 있고, 함께 움직였다면 입력 구성 변화가 중요한 원인 후보로 남습니다.

이 Lab의 핵심은 점수 분포와 예측 분포를 함께 읽어 입력 변화, 모델 변경, 임계값 변경 후보를 분리하는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/05_qa_strategy/score-prediction-distribution.md` | 점수와 예측 분포 변화의 의미와 배포 판단 해석 확인 |
| 초급 Notebook | `labs/ch05_qa_strategy/01_collect_release_evidence.ipynb` | score/prediction 분포와 변화 지표 확인 |
| Lite Notebook | `jupyterlite/files/05_qa_strategy/01_collect_release_evidence.ipynb` | 브라우저에서 score/prediction 분포 확인 |
| 참고 Notebook | `labs/ch05_qa_strategy/03_qa_strategy_lab.ipynb` | 전체 5장 흐름을 한 번에 다시 볼 때 사용 |
| CLI 산출물 생성 | `labs/ch05_qa_strategy/04_build_qa_artifacts.py` | 점수 평균, `high_risk` 비율 변화, 입력 구성 변화 리포트 생성 |

!!! note "브라우저 실습"
    설치 없이 확인하려면 <a href="../../jupyterlite/lab/index.html?path=05_qa_strategy/01_collect_release_evidence.ipynb">JupyterLite에서 릴리스 근거 모으기</a>를 엽니다. 이 경로에서는 점수와 예측 분포를 준비된 확인 결과와 함께 확인합니다.

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

입력 분포와 예측 분포는 함께 해석해야 합니다. [Evidently의 data drift와 prediction drift 해석 글](https://www.evidentlyai.com/blog/data-and-prediction-drift)은 입력 변화와 출력 변화가 같은 방향인지, 서로 어긋나는지에 따라 원인 후보가 달라진다고 설명합니다. 본 과정에서는 이 관점을 아래처럼 QA 조사 표로 좁혀 사용합니다.

| 입력 분포 | 점수/예측 분포 | 우선 원인 후보 | 배포 판단 해석 |
| --- | --- | --- | --- |
| 변함 | 변함 | current batch case-mix shift, upstream 입력 변경, 모델 버전 변경 | 입력 변화와 출력 변화가 연결되는지 5-3에서 추적 |
| 변함 | 안정 | 모델이 해당 변화에 둔감하거나 변화가 영향 없는 구간 | 영향 제한 가능성을 남기되 label 기반 재확인 필요 |
| 안정 | 변함 | 임계값 변경, 모델 버전 변경, 후처리/집계 오류 | 설정값과 배포 이력 먼저 확인 |
| 안정 | 안정 | 즉시 운영 이상 신호 낮음 | label 지연이 있으면 정답 도착 후 성능 재확인 |

이 표의 목적은 원인을 빠르게 단정하는 것이 아닙니다. 예를 들어 입력과 예측이 모두 움직였다고 해서 바로 재학습을 결정하지 않습니다. 먼저 validation failure, `model_version`, `threshold`, source system, trace 로그를 확인해 데이터 품질 문제와 설정 문제를 분리합니다.

## 5-2-3. 특정 클래스 예측 급증 분석

실습 목표는 평균 점수(score average)와 `high_risk` 예측 비율 변화를 비교하는 것입니다.

이 단계의 준비 데이터는 정상/이상 예측 이벤트를 같은 기준으로 비교하기 위한 근거입니다. 준비 데이터는 앞 장에서 생성한 정상/이상 예측 이벤트(prediction event)입니다. 전체 코드는 `packages/ai-quality/src/ai_quality/qa_strategy/application/analyze_prediction_shift.py`에 있으며, 문서에서는 코드보다 점수와 예측 분포 변화의 해석에 집중합니다.

이 실행에서 확인할 핵심은 평균 점수 변화와 `high_risk` 비율 변화가 같은 방향으로 움직였는지입니다. Notebook에서는 `labs/ch05_qa_strategy/01_collect_release_evidence.ipynb`의 score/prediction distribution 셀을 실행합니다. 명령행에서 리포트 산출물을 다시 만들 때는 `uv run --group lab python labs/ch05_qa_strategy/04_build_qa_artifacts.py`를 사용합니다.

이 출력에서 확인할 핵심은 입력 구성 변화가 점수와 예측 변화의 원인 후보로 남을 만큼 동반되는지입니다.

| 비교 항목 | 기준선 | current | 변화량 |
| --- | --- | --- | --- |
| 평균 score | `0.5020` | `0.6402` | `+0.1382` |
| `high_risk` 예측 비율 | `0.2167` | `0.4583` | `+0.2417` |

수강생은 이 값을 5-1 입력 분포 변화와 연결합니다. `heart_rate` 평균이 올라가고 `oxygen_saturation` 평균이 낮아진 상태에서 평균 점수와 `high_risk` 비율도 함께 증가했습니다. 따라서 current batch 입력 구성 변화는 중요한 원인 후보입니다. 다만 모델 버전, 임계값, 검증 실패를 함께 확인하기 전까지는 확정 원인으로 쓰지 않습니다.

실패 시 확인 포인트는 예측 이벤트(prediction event) 로그 생성 여부, 필드(field) 이름, 임계값 값입니다. 점수와 예측이 로그에 없으면 분포 분석을 할 수 없습니다.

## 5-2-4. 임계값 기준 FP/FN 변화 해석

임계값은 점수를 예측으로 바꾸는 기준입니다. 운영 중 임계값이 바뀌면 점수 분포가 그대로여도 예측 분포가 바뀔 수 있습니다.

수강생은 임계값 근처 샘플에 주의해야 합니다. 점수가 0.49~0.51에 몰려 있다면 임계값을 조금만 바꿔도 예측이 크게 바뀔 수 있습니다. 이런 상황에서는 배포 전 임계값 변경 영향 분석이 필요합니다.

| 점수 위치 | 배포 판단 해석 |
| --- | --- |
| 임계값보다 충분히 낮음 | 임계값 변경에 덜 민감 |
| 임계값 근처 | 작은 설정 변경에도 예측이 바뀔 가능 |
| 임계값보다 충분히 높음 | Positive 예측이 안정적일 수 있음 |

이 내용은 2장의 임계값 분석과 연결됩니다. 배포 전 평가에서는 임계값별 FP/FN을 확인하고, 운영에서는 점수 분포와 예측 분포로 임계값 영향을 감시합니다.
