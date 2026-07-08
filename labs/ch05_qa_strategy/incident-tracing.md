# 5-3. 운영 이상 징후 탐지와 원인 추적 [Lab]

5-3 Lab의 목표는 5-1의 current batch 입력 구성 변화, 5-2의 점수와 예측 분포 변화, 4장의 운영 관측 신호를 하나의 원인 후보 표로 연결하는 것입니다. 이상 징후 분석은 하나의 지표를 보고 바로 원인을 단정하는 활동이 아니라, 후보를 줄여 가는 활동입니다.

이 Lab의 핵심은 입력, 점수, 운영 신호를 원인 후보와 owner가 있는 추적표로 바꾸는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/05_qa_strategy/incident-tracing.md` | 이상 징후 분석 순서와 원인 후보 정리 방식 확인 |
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
uv run --group lab python labs/ch05_qa_strategy/build_qa_artifacts.py
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
