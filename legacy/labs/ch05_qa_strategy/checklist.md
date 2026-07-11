# 5-8. 최종 확인 결과 정리 [Lab]

5-8 Lab의 목표는 앞에서 만든 입력 구성 변화 리포트(`drift_report.md`), 예측 변화 리포트, 원인 후보, Argo CD/KServe 확인 결과, 승인/보류 판단을 최종 체크리스트로 묶는 것입니다. 체크리스트는 외우는 목록이 아니라, 품질 판단의 근거, 차단 상태, 다음 조치를 남기는 실무 산출물입니다.

**이 Lab에서는 새 분석을 많이 추가하지 않습니다.** 5-1부터 5-6까지 만든 산출물을 다시 연결해 “무엇을 확인했고, 어떤 근거가 있으며, 다음에 무엇을 해야 하는가”를 한 장으로 정리합니다.

이 Lab의 핵심은 앞 단계 확인 결과를 조건부 보류와 재평가 조건이 있는 최종 판단으로 묶는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `docs/05_qa_strategy/checklist.md` | 최종 체크리스트 구성과 배포 판단 예시 확인 |
| 초급 Notebook | `labs/ch05_qa_strategy/02_read_release_report.ipynb` | release report의 근거, owner, next action 확인 |
| Lite Notebook | `jupyterlite/files/05_qa_strategy/02_read_release_report.ipynb` | 브라우저에서 체크리스트 근거 artifact 확인 |
| 참고 Notebook | `labs/ch05_qa_strategy/03_qa_strategy_lab.ipynb` | 전체 5장 흐름을 한 번에 다시 볼 때 사용 |
| CLI 스크립트 | `labs/ch05_qa_strategy/04_build_qa_artifacts.py` | 체크리스트 템플릿과 이번 사건 제출용 `ai_qa_checklist.md` 생성 |

!!! note "브라우저 실습"
    설치 없이 확인하려면 <a href="../../jupyterlite/lab/index.html?path=05_qa_strategy/02_read_release_report.ipynb">JupyterLite에서 릴리스 보고서 확인</a>을 엽니다. 이 경로에서 확인한 내용은 최종 체크리스트의 prepared 확인 결과 확인 근거로만 기록합니다.

실습 준비물은 다음과 같습니다. 앞 단계 산출물이 없으면 체크리스트는 형식만 남고 판단 근거가 비게 됩니다.

| 준비물 | 확인할 내용 |
| --- | --- |
| `drift_report.md` | current batch 입력 특성(feature) 분포 변화를 담은 입력 구성 변화 리포트 |
| `label_basis_check.md` | 라벨 허용값, 라벨 매핑, 클래스별 표본 수 |
| 5-2 예측 변화 출력 | 점수(score) 평균과 `high_risk` 예측 비율 변화 |
| `quality_issue_trace.md` | 원인 후보, owner, audit reference, 다음 확인 항목 |
| `release_approval.md` | 승인 여부, 실패 기준, live Argo CD/KServe 미검증 항목, 승인/보류 리스크, 재평가 조건 |
| `configs/qa_strategy/qa_checklist.yaml` | 반복 사용 체크리스트 항목 |

최종 체크리스트에는 data lineage도 함께 남깁니다. 여기서 lineage는 별도 플랫폼 화면이 아니라, **이번 판단에 사용한 데이터와 산출물이 어느 단계에서 파생되었는지 보여주는 근거 연결표**입니다. 이 연결표가 있어야 reviewer가 “test 결과인지, 운영 current batch 결과인지, validation 재현 결과인지”를 구분할 수 있습니다.

| 판단 단계 | 근거 데이터 | 근거 산출물 | 보고서에서 지켜야 할 경계 |
| --- | --- | --- | --- |
| 평가 가능성 확인 | `vital_signs_evaluation_baseline.csv` | `chapter_01_quality_report.md` | 1장 결론을 운영 입력 정상으로 확대하지 않음 |
| 모델 기준 평가 | `vital_signs_train.csv`, `vital_signs_test.csv` | `model_test_eval.json` | test는 선택된 모델과 threshold의 최종 모델 평가에만 사용 |
| 데이터 조건 변화 비교 | `vital_signs_valid_baseline.csv`, `vital_signs_valid_degraded.csv` | `validation_degradation_comparison.json` | 품질 저하 validation 비교를 운영 root cause 확정으로 쓰지 않음 |
| 운영 current 관측 | `serving_requests_current.csv`, `operational_current_events.jsonl` | `drift_report.md`, `quality_issue_trace.md` | current batch 입력 구성 변화와 검증 실패를 후보 근거로 표현 |
| 배포 판단 | `release_regression_cases.csv`, Argo CD/KServe 확인 결과 | `release_approval.md`, `ai_qa_checklist.md` | 조건부 보류와 재평가 조건을 owner와 확인 경로로 남김 |

이 표는 수강생이 최종 보고서에 붙일 수 있는 감사 추적(audit trail)의 최소 형태입니다. 예를 들어 `high_risk` 비율 증가를 쓸 때는 `model_test_eval.json`이 아니라 `drift_report.md`와 `operational_current_events.jsonl`을 근거로 삼아야 합니다. 반대로 모델 자체 성능 기준을 말할 때는 운영 로그가 아니라 `model_test_eval.json`과 approval rule을 확인해야 합니다.

## 5-8-1. 데이터 품질 체크리스트

데이터 품질 체크리스트는 모델 평가의 출발 조건을 확인합니다. 필수 컬럼(column), 결측값, 이상치, 라벨(label), 관심 클래스 표본 수(Positive support), 클래스(class) 비율, 파생 특성을 봅니다.

이 항목은 1장과 2장에서 다룬 데이터 품질 확인을 5장의 운영 판단으로 다시 가져오는 역할을 합니다. 예를 들어 `oxygen_saturation` 분포가 기준선(baseline)과 달라졌다면, 체크리스트에는 “확인 완료”만 표시하지 않고 어떤 리포트에서 어떤 변화가 보였는지 함께 남겨야 합니다.

데이터 품질 체크리스트는 다음 질문으로 해석합니다.

| 확인 항목 | QA 해석 |
| --- | --- |
| 필수 컬럼(column) 존재 | 평가와 서빙 입력 조건이 유지되는가 |
| 중복 행, 빈 컬럼, 상수 컬럼 | 평가 데이터가 반복/고정값 때문에 지표를 왜곡하지 않는가 |
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

Monitoring strategy 항목은 “대시보드가 있다”보다 넓은 질문입니다. [Evidently의 model monitoring 설명](https://www.evidentlyai.com/ml-in-production/model-monitoring)은 모니터링의 목적, 대상자, metric 선택, reference dataset, 실행 주기를 정해야 한다고 설명합니다. 본 과정에서는 이 관점을 최종 체크리스트의 owner와 재평가 조건으로 바꿔 사용합니다.

| 전략 항목 | QA 체크 질문 | 이번 사건 보고서에 남길 내용 |
| --- | --- | --- |
| 목적 | 어떤 결정을 돕는 모니터링인가 | 17시 릴리스 회의의 승인/조건부 보류 판단 |
| 대상자 | 누가 보고 조치하는가 | QA Lead, Deployment Owner, Data Engineering, Client Integration |
| Reference | 무엇을 기준선으로 삼는가 | `serving_requests_valid.csv`, baseline operational metrics |
| Current 기간 | 어떤 구간을 current로 보는가 | 이상 신호가 관측된 current batch와 streaming window |
| Proxy metric | label 없이 무엇을 먼저 볼 것인가 | 입력 분포, score bucket, prediction 분포, validation failure |
| Label 재평가 | 정답이 들어오면 무엇을 다시 볼 것인가 | Precision, Recall, FP/FN, threshold 영향 |
| Trigger | 언제 조사 또는 보류로 넘기는가 | 기준 초과, 추적 불가, label 부재 상태의 큰 proxy 이동 |

이 항목은 `configs/qa_strategy/qa_checklist.yaml`에도 들어갑니다. 따라서 `04_build_qa_artifacts.py`를 실행하면 최종 `ai_qa_checklist.md`에 기준선과 current 기간, proxy metric, 재평가 조건을 남길 수 있습니다.

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

핵심 로직은 `packages/ai-quality/src/ai_quality/qa_strategy/application/build_qa_checklist.py`에 있습니다. 설정 파일의 섹션과 항목을 읽어 체크리스트 산출물로 바꾸는 구조이지만, 수강생이 확인할 핵심은 코드가 아니라 최종 산출물이 같은 확인 결과 path 기준으로 만들어졌는지입니다. 로컬에서 재생성할 때는 `labs/ch05_qa_strategy/04_build_qa_artifacts.py`를 사용하고, 읽기 전용 확인에서는 준비된 report artifact를 확인합니다.

이 출력에서 확인할 핵심은 라벨 기준, 승인 판단, 체크리스트 템플릿, 제출용 점검본이 모두 생성되었는지입니다.

| 생성 산출물 | 확인할 경로 |
| --- | --- |
| 라벨 기준 확인 | `artifacts/reports/label_basis_check.md` |
| 승인 판단 | `artifacts/reports/release_approval.md` |
| 체크리스트 템플릿 | `artifacts/reports/ai_qa_checklist_template.md` |
| 제출용 점검본 | `artifacts/reports/ai_qa_checklist.md` |

이 산출물들은 최종 보고서의 판단, 확인 결과 path, owner, next action을 뒷받침합니다.

| 파일 | 내용 |
| --- | --- |
| `artifacts/reports/ai_qa_checklist_template.md` | 데이터 품질, 모델 품질, 서빙 품질, 운영 관측, 이상 징후 보고 체크리스트 템플릿 |
| `artifacts/reports/ai_qa_checklist.md` | 이번 사건 제출용 점검본, 항목별 상태, 근거, 배포 note, 담당, 다음 조치 |
| `artifacts/reports/label_basis_check.md` | `high_risk`, `low_risk` 허용값과 표본 수, invalid/missing count |

**`ai_qa_checklist_template.md`는 반복 점검 템플릿이고, `ai_qa_checklist.md`는 이번 사건에 값을 채운 제출용 sign-off입니다.** 제출용 파일은 체크박스만 보여주지 않고 `pass`, `fail`, `unverified`, `보류` 같은 상태와 확인 결과 path, 담당자, 다음 조치를 함께 남깁니다. 따라서 수강생은 최종 보고서에 아래 내용을 체크리스트 행으로 연결해 제출합니다.

| 보고 항목 | 이번 실습에서 남길 내용 |
| --- | --- |
| 최종 판단 | `recommendation=conditional_보류`, `approved=False`이므로 조건부 보류와 재평가 필요 |
| 실패 기준 | `recall=0.5926`, `error_rate=0.0667` |
| 라벨 기준 | `label_basis_check.md`에서 `invalid_count=0`, `missing_count=0`, `high_risk=37`, `low_risk=33` |
| 미검증 리스크 | `release_approval.md`에서 `live_deployment=unverified` |
| 확인 owner | `Data Engineering`, `ML Engineering`, `Client Integration`, `Platform/MLOps`, `QA Lead`, `Deployment Owner` |
| 감사 추적 | `quality_issue_trace.md`의 audit reference와 검증 실패 대표 요청 |
| 재평가 조건 | owner별 next action 완료 후 같은 approval rule로 재실행 |

최종 확인 결과의 마무리 기준은 다음과 같습니다.

| 완료 조건 | 확인 |
| --- | --- |
| 입력 분포 변화 확인 | `drift_report.md` 생성 |
| 라벨 기준 확인 | `label_basis_check.md` 생성 |
| 점수와 예측 변화 확인 | 5-2 출력 확인 |
| 원인 후보 추적 | `quality_issue_trace.md` 생성 |
| 승인/조건부 보류 판단 | `release_approval.md` 생성 |
| 체크리스트 템플릿 | `ai_qa_checklist_template.md` 생성 |
| 제출용 점검본 | `ai_qa_checklist.md`에서 `배포 준비 상태=blocked`, `status=보류`, `live_deployment=unverified`, owner와 next action 확인 |

실패 시에는 먼저 `configs/qa_strategy/qa_checklist.yaml` 문법을 확인합니다. 체크리스트 항목 수가 문서와 다르면 설정 파일이 변경되었는지 확인하고, 산출물 파일이 생성되지 않으면 `artifacts/reports/` 경로 쓰기 권한과 실행 위치를 확인합니다.

**배포 판단의 결론은 모델 지표 하나로 끝나지 않는다는 점입니다.** 데이터 분포, 점수, 예측, 임계값, GitOps sync, KServe readiness, API 계약(contract), 오류율, 지연 시간, 로그 추적 가능성을 함께 보고, 근거 기반으로 배포, 보류, 되돌림 조건을 판단해야 합니다.
