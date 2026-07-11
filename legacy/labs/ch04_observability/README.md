# 4-6. 운영 품질 관측 실습

4-6 Lab의 목표는 정상 상태와 이상 상태의 로그, 메트릭, 대시보드 산출물을 비교해 운영 품질 신호를 해석하는 것입니다. 모델을 다시 학습하는 실습이 아니라, 운영 중 남겨야 할 필드(field)와 지표(metric)를 만들고 QA 코멘트로 정리하는 실습입니다.

4-5에서 대시보드 패널(panel)을 해석했다면, 4-6에서는 그 패널의 근거가 되는 파일을 직접 생성합니다. **수강생은 정상 기준선(baseline)과 이상 상태(anomaly)를 비교하고, `request_id`, `trace_id`, `model_version`, `score`, `threshold`, `prediction`, `validation_failure`가 원인 추적에 어떻게 쓰이는지 확인합니다.**

이 Lab의 핵심은 정상/이상 운영 산출물을 비교해 원인 후보를 보고서 문장으로 바꾸는 것입니다.

| 산출물 | 경로 | 사용 방식 |
| --- | --- | --- |
| Lab 문서 | `labs/ch04_observability/README.md` | 운영 관측 실습 흐름과 QA 해석 확인 |
| 초급 Notebook 1 | `labs/ch04_observability/01_read_logs.ipynb` | JSONL 로그에서 요청 단위 필드 확인 |
| 초급 Notebook 2 | `labs/ch04_observability/02_compare_operational_numbers.ipynb` | 오류율, 지연 시간, score, prediction 변화 비교 |
| 참고 Notebook | `labs/ch04_observability/03_observability_lab.ipynb` | 전체 운영 관측 흐름을 한 번에 다시 볼 때 사용 |
| CLI 스크립트 | `labs/ch04_observability/*.py` | Notebook과 같은 흐름을 명령행에서 단계별 실행 |

## 4-6-1. 정상 상태의 로그와 지표 확인

실습 목표는 정상 기준선과 이상 상태(anomaly)를 비교할 수 있는 구조화 로그를 만드는 것입니다. 기준선이 없으면 현재 값이 높은지 낮은지 판단하기 어렵습니다. 운영 관측에서도 비교 기준이 필요합니다.

| 항목 | 내용 |
| --- | --- |
| 실습 목표 | 정상/이상 예측 이벤트(prediction event)를 JSONL 로그로 생성 |
| 준비 데이터 | 코드로 생성하는 정상 상태와 이상 상태 이벤트 |
| 실행 코드 | `labs/ch04_observability/04_build_observability_artifacts.py` |
| 예상 결과 | 정상 로그와 이상 로그 JSONL 파일 생성 |
| QA 해석 | 기준선이 있어야 현재 상태가 이상인지 판단 가능 |
| 실패 시 확인 | `artifacts/logs` 디렉터리와 파일 경로 확인 |

이 실행은 정상/이상 로그와 메트릭을 만들어 운영 품질 비교의 기준 증거를 생성합니다. 실행 환경은 저장소 루트의 로컬 shell이며, 실행 코드는 다음과 같습니다.

```bash
uv run --group lab python labs/ch04_observability/04_build_observability_artifacts.py
```

실행 후 다음 파일이 생성됩니다.

```text
artifacts/logs/chapter_04_normal_events.jsonl
artifacts/logs/chapter_04_anomaly_events.jsonl
```

이 파일은 보고서용 120건 current incident sample로 생성됩니다. 다만 Grafana Cloud streaming Demo는 같은 종류의 JSONL 로그를 계속 append할 수 있으므로, 수강생은 숫자를 인용하기 전에 `artifacts/metrics/chapter_04_anomaly.prom`의 `ai_quality_request_total`과 로그 행 수가 같은 사건 단위를 가리키는지 확인합니다. 행 수가 120건보다 많다면 streaming 실행 이력이 섞인 상태일 수 있으므로 `uv run --group lab python labs/ch04_observability/04_build_observability_artifacts.py`로 보고서용 산출물을 다시 만든 뒤 인용합니다.

**QA 해석에서는 정상 로그와 이상 로그의 필드가 같은지 먼저 확인합니다.** 필드 구조가 다르면 대시보드 비교가 어렵습니다. 그다음 요청 수(request count), 오류(error), 검증 실패(validation failure), 점수(score), 예측(prediction), 지연 시간(latency)을 비교합니다.

로그가 생성되지 않으면 이후 메트릭(metric)과 대시보드 실습도 진행할 수 없습니다. 이 단계가 4장 Lab의 출발점입니다.

## 4-6-2. request_id로 대표 요청 확인

실습 목표는 이상 상태 로그에서 대표 요청 하나를 찾아 실제 필드를 확인하는 것입니다. 대시보드에서 이상 신호를 발견해도 개별 요청 로그가 없으면 원인 후보를 좁히기 어렵습니다.

| 항목 | 내용 |
| --- | --- |
| 실습 목표 | `request_id`로 이상 상태 대표 요청 조회 |
| 준비 데이터 | `artifacts/logs/chapter_04_anomaly_events.jsonl` |
| 실행 코드 | `labs/ch04_observability/01_read_logs.ipynb` |
| 예상 결과 | `current-0008` 요청의 `trace_id`, `score`, `prediction`, `latency_ms` 확인 |
| QA 해석 | 대표 요청의 점수, 임계값(threshold), 예측을 근거로 원인 후보를 좁힘 |
| 실패 시 확인 | 4-6-1 로그 생성 여부와 `request_id` 값 확인 |

이 실행에서 확인할 핵심은 대표 요청의 `trace_id`, 점수, 임계값, 예측, 지연 시간이 함께 추적되는지입니다. Notebook에서는 `labs/ch04_observability/01_read_logs.ipynb`의 `request_id` 조회 셀을 실행합니다. 명령행에서 로그와 메트릭 산출물을 다시 만들 때는 `uv run --group lab python labs/ch04_observability/04_build_observability_artifacts.py`를 사용합니다.

이 출력에서 확인할 핵심은 대표 요청 하나가 대시보드 신호를 추적할 수 있는 필드를 갖는지입니다. 예상 결과는 다음과 같은 형태입니다.

```text
request_id=current-0008
{
  "timestamp": "2026-01-01T09:00:20+00:00",
  "request_id": "current-0008",
  "trace_id": "current-trace-0002",
  "model_version": "v1",
  "score": 0.9616,
  "threshold": 0.5,
  "prediction": "high_risk",
  "latency_ms": 180.0,
  "status_code": 200,
  "validation_failure": false
}
```

**QA는 이 요청 하나만으로 전체 원인을 확정하지 않습니다.** 다만 대표 요청을 통해 로그에 추적에 필요한 필드가 남아 있는지 확인하고, 같은 `trace_id`에 묶인 다른 이벤트를 함께 볼 준비를 합니다.

## 4-6-3. 메트릭 생성과 정상/이상 비교

실습 목표는 이상 상태 로그를 메트릭으로 집계하고, 정상 기준선과 비교해 변화량을 해석하는 것입니다. 메트릭은 개별 요청의 상세 원인을 말해 주지는 않지만, 변화 규모와 방향을 빠르게 보여줍니다.

| 항목 | 내용 |
| --- | --- |
| 실습 목표 | Prometheus 형식 메트릭 생성과 정상/이상 상태 비교 |
| 준비 데이터 | 정상/이상 JSONL 로그 |
| 실행 코드 | `02_compare_operational_numbers.ipynb`, `04_build_observability_artifacts.py` |
| 예상 결과 | 오류율(error rate), 지연 시간, 전체 이벤트와 유효 요청 기준 `high_risk` 비율, 평균 점수 증가 확인 |
| QA 해석 | 입력 검증 실패, 운영 부하, 입력 분포 변화 후보 분리 |
| 실패 시 확인 | 정상 상태와 이상 상태 로그 파일, 메트릭 계산 대상 확인 |

Prometheus text 형식의 메트릭은 정상/이상 상태의 변화 규모를 비교하는 증거입니다. 먼저 메트릭을 생성합니다.

```bash
uv run --group lab python labs/ch04_observability/04_build_observability_artifacts.py
```

핵심 출력은 다음과 같습니다.

```text
ai_quality_request_total 120
ai_quality_error_total 8
ai_quality_validation_failure_total 8
ai_quality_latency_average_ms 223.750
ai_quality_score_average 0.640249
ai_quality_high_risk_rate 0.458333
ai_quality_valid_request_total 112
ai_quality_valid_score_average 0.643703
ai_quality_valid_high_risk_rate 0.464286
```

정상 기준선과 이상 상태(anomaly) 비교는 `labs/ch04_observability/02_compare_operational_numbers.ipynb`의 정상/이상 비교 셀에서 확인합니다.

이 출력에서 확인할 핵심은 오류율, 지연 시간, `high_risk` 비율, 평균 점수가 같은 방향으로 변했는지입니다. 예상 결과는 다음과 같은 형태입니다.

```text
baseline_error_rate=0.0000
current_error_rate=0.0667
latency_delta_ms=120.00
high_risk_rate_delta=0.2417
average_score_delta=0.1382
notes=
- 오류율이 증가했습니다. 검증 실패를 확인합니다.
- 지연 시간이 증가했습니다. 서비스 부하나 의존성 지연을 확인합니다.
- 예측 분포가 high_risk 쪽으로 이동했습니다.
- 점수 분포가 높은 방향으로 이동했습니다.
```

**이 결과는 오류율, 지연 시간, `high_risk` 비율, 평균 점수(average score)가 모두 증가한 상황입니다.** QA는 원인을 하나로 단정하지 않고 입력 검증 실패, 운영 부하, 입력 분포 변화 후보를 나눠 봅니다.

이 Lab의 `ai_quality_score_average`와 `ai_quality_high_risk_rate`는 전체 이벤트 기준입니다. 즉 검증 실패로 표시된 요청도 서비스 영향 범위에는 포함됩니다. 모델 응답 경향을 따로 볼 때는 `ai_quality_valid_score_average`, `ai_quality_valid_high_risk_rate`처럼 검증 실패를 제외한 유효 요청 기준 지표를 함께 사용합니다.

QA 해석은 다음처럼 정리할 수 있습니다.

| 관측 | 원인 후보 |
| --- | --- |
| 오류율 증가 | API 오류, 검증 실패 |
| 지연 시간 증가 | 트래픽(traffic) 증가, 처리 지연 |
| `high_risk` 비율 증가 | 입력 분포 변화, 임계값 변경 |
| 평균 점수 증가 | 특성(feature) 분포 변화, 모델 버전(model_version) 변경 |

이 표는 결론이 아니라 다음 확인 순서입니다. 4-6-4에서는 검증 실패를 따로 보고, 4-6-5에서는 대시보드와 페이로드 미리보기(payload preview)로 산출물을 확인합니다.

## 4-6-4. 검증 실패 증가 분석

**검증 실패가 증가하면 모델 지표보다 API 입력 품질을 먼저 확인해야 합니다.** 입력이 잘못된 요청을 메트릭 계산이나 모델 품질 평가에 그대로 섞으면 품질 이상 원인을 잘못 해석할 수 있습니다.

| 확인 기준 | 확인 방법 |
| --- | --- |
| 어떤 요청(request)이 실패했는가 | `request_id`로 로그를 조회 |
| 문제 입력 필드 확인 | 오류 응답과 검증 실패 로그 확인 |
| 특정 클라이언트(client) 한정 실패 여부 | 로그/메트릭 라벨(label) 또는 `trace_id` 흐름 확인 |
| 모델 버전 변경과의 중복 여부 | `model_version`과 배포 시간 확인 |

QA 해석에서는 검증 실패를 운영 품질 문제로 기록합니다. 모델이 요청을 처리하지 못한 것이 아니라 입력 계약(contract)이 깨진 것이므로, 후속 조치는 API 스키마(schema), 클라이언트 페이로드(client payload), 상위 시스템(upstream) 데이터 생성 로직 확인으로 이어져야 합니다.

실습 산출물 `artifacts/reports/chapter_04_validation_failure_examples.md`는 대표 실패 요청을 owner와 함께 정리합니다. 예를 들어 `current-0000`은 `client_id=partner-feed-v2`, `source_system=upstream-partner-feed`, `failed_field=oxygen_saturation`, `error_category=schema_validation`, `owner=Client Integration`으로 기록됩니다. 이 증거가 있어야 “검증 실패 8건”을 단순 숫자가 아니라 조치 가능한 업무로 바꿀 수 있습니다.

## 4-6-5. 추론 분포 변화 확인

마지막 Lab은 이상 상태(anomaly) 기준의 대시보드 JSON(dashboard JSON), Grafana Cloud 페이로드 미리보기(payload preview), Tempo trace preview, drift 후보 metric을 생성합니다.

```bash
uv run --group lab python labs/ch04_observability/04_build_observability_artifacts.py
```

수강생은 `artifacts/grafana/ai_quality_overview_dashboard.json`과 `artifacts/grafana/ai_quality_details_dashboard.json`을 열어 패널 쿼리(panel query)를 확인하고, `artifacts/grafana/grafana_cloud_payload_preview.json`에서 라벨과 로그 필드가 충분한지 확인합니다. Tempo 연결을 진행하지 않는 경우에도 `artifacts/traces/chapter_04_tempo_payload.json`을 열어 `course_trace_id`와 span 이름이 요청 흐름을 설명하는지 확인합니다.

| 산출물 | 확인할 점 |
| --- | --- |
| 대시보드 JSON(dashboard JSON) | 패널 제목(panel title), 쿼리(query), 데이터소스(datasource) 연결 대상 |
| 페이로드 미리보기(payload preview) | `service`, `environment` 라벨과 로그 필드 |
| Tempo trace preview | `POST /predict`, `validate_payload`, `score_model`, `emit_observability`, `course_trace_id` |
| 검증 실패 예시 | `client_id`, `source_system`, `failed_field`, `error_detail`, `owner` |
| 운영 품질 해석 리포트 | `input_case_mix_shift`로 기록된 입력 구성 변화, `prediction_shift`, `api_validation`, `service_latency` 후보와 next action |
| Prometheus text 형식 | 메트릭 이름(metric name), drift 후보 metric, 값의 의미 |
| Loki 쿼리 예시 | `request_id`, `trace_id`, 검증 실패 조회 |

**최종 해석은 “운영에서 이상 신호를 발견했을 때 어떤 데이터를 근거로 보고할 것인가”입니다.** 발견한 값, 기준선과의 차이, 원인 후보, 추가 확인이 필요한 로그나 설정값을 함께 정리해야 합니다.

**운영 품질 관측의 결론은 AI 서비스 운영 품질을 오류(error)와 지연 시간만으로 판단하지 않는다는 점입니다.** `score`, `threshold`, `prediction`, `model_version`, `validation_failure`, `failed_field`, `client_id`, `source_system`을 함께 기록하고, 대시보드(dashboard), 메트릭, 로그(log)를 연결해서 봐야 데이터 문제, 모델 자체 문제, API 문제, 설정 문제를 구분할 수 있습니다.
