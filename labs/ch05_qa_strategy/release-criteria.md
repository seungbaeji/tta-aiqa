# 5-6. 배포 승인과 운영 전환 기준 [Core]

배포 승인 판단은 모델 지표(metric) 하나로 정하지 않습니다. 5-5에서 테스트 데이터 묶음을 나누었다면, 5-6에서는 그 결과를 데이터 조건, 모델 지표, API 계약(contract), 운영 관측 준비, 설정 일치성으로 묶어 승인 또는 보류 판단으로 정리합니다.

배포 승인은 “모델 지표가 기준을 넘었는가”보다 넓은 질문입니다. [Model Cards for Model Reporting](https://research.google/pubs/pub48120/)의 관점처럼 모델은 사용 목적(intended use), 평가 특성, 제한 사항을 함께 설명해야 합니다. QA의 승인/보류 판단도 마찬가지입니다. 어떤 데이터와 기준에서는 승인 가능한지, 어떤 제한이 있는지, 운영에서 어떤 신호를 봐야 하는지를 함께 남겨야 합니다.

승인 판단에 들어가는 입력은 다음과 같습니다. 이 표는 한 항목이라도 실패하면 무조건 같은 조치를 한다는 뜻이 아니라, 어떤 근거가 어떤 위험을 설명하는지 분리하기 위한 기준입니다.

| 승인 판단 입력 | 확인 내용 | 기준 미달 시 해석 |
| --- | --- | --- |
| 데이터 검증 결과 | 필수 컬럼, 라벨(label), 관심 클래스 표본 수(Positive support) | 평가 결과 자체를 제한적으로 해석 |
| 모델 지표 | 정밀도(Precision), 재현율(Recall), PR-AUC, FP/FN | 품질 기준 미달 또는 추가 임계값(threshold) 검토가 필요 |
| API 계약 | 입력 스키마(schema), 오류 응답, `request_id` | 운영 요청 처리와 추적이 불안정 |
| Live 배포 확인 결과 | `/health`, `/predict`, Pod readiness, 응답 `model_version`, `threshold` | 실제 운영 환경 준비를 승인 근거로 쓰기 어려움 |
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
uv run --group lab python labs/ch05_qa_strategy/04_build_qa_artifacts.py
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
- approve_now risk: 기준 미달 지표와 미검증 live 확인 결과를 운영에 반영할 수 있음
- conditional_hold risk: 배포 지연과 현재 운영 버전 유지 부담이 생김
- 실패한 기준을 검토할 때까지 배포를 보류합니다.
<repo>/artifacts/reports/release_approval.md
```

이 산출물은 승인 여부, 실패 기준, owner, 재평가 조건을 보고서에 연결하는 근거입니다.

| 파일 | 내용 |
| --- | --- |
| `artifacts/reports/release_approval.md` | 승인 여부, 실패한 기준, 관측값, 기준값, 미검증 운영 리스크, 승인/보류 리스크, owner, 재평가 조건 |

**QA 해석에서는 `approved=False` 자체보다 실패 기준별 관측값을 먼저 읽습니다.** 위 예시는 Precision은 `1.0000`으로 최소 기준 `0.6000`을 통과했지만, Recall은 `0.5926`으로 최소 기준 `0.6000`에 근소하게 미달하고 error rate가 `0.0667`로 최대 기준 `0.0500`을 초과한 상황입니다. `prepared_api_contract=True`는 준비된 계약 확인이 통과했다는 의미이지 live 배포 검증이 끝났다는 의미가 아닙니다. 따라서 다음 조치는 모델만 재학습하는 것이 아니라 평가 데이터, 임계값, 오류 로그, 운영 이벤트, live smoke 확인 결과를 함께 확인하는 쪽으로 잡아야 합니다.

보고서 문장은 다음처럼 양쪽 리스크를 모두 남깁니다.

| 판단 | 리스크 | 근거 | 재평가 조건 |
| --- | --- | --- | --- |
| 승인 | 기준 미달 상태가 운영에 반영되어 FN과 오류 요청이 증가할 수 있음 | `recall`, `error_rate` 실패 | 실패 기준 재측정과 검증 실패 원인 확인 |
| 보류 | 배포 지연과 현재 운영 버전 유지 부담이 생김 | `latency`, `prepared_api_contract`는 통과하지만 `live_deployment`는 미검증 | owner별 next action 완료 후 같은 기준으로 재평가 |
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

**QA 코멘트에는 “API 정상”처럼 넓게 쓰지 않습니다.** “필수 입력 누락 시 오류 응답 확인”, “응답에 `model_version`과 `threshold` 포함”, “로그에서 `request_id` 검색 가능”처럼 승인 기준을 관측 가능한 항목으로 남깁니다. 이번 로컬 실습에서는 live Kubernetes 요청을 필수로 실행하지 않으므로, live 확인 결과가 없으면 “운영 배포 검증 완료”라고 쓰지 않고 `live_deployment=unverified`로 남깁니다.

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
