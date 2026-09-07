# Risk API

## 1. 역할

### 1-1. Inbound API

Feature contract를 검증하고 mortality-risk score, threshold와 prediction을 반환합니다. Compose에서는 local sklearn, Kubernetes에서는 KServe HTTP adapter를 사용합니다.

## 2. 실행

### 2-1. 권장 경로

```bash
docker compose -f deploy/compose.yaml up -d --build
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
```

## 3. Runtime 계약

### 3-1. Endpoint

- `/health/live`: process 상태
- `/health/ready`: model backend readiness
- `/v1/model`: profile, version, threshold
- `/v1/predict`: prediction과 `education_only` 사용 경계
- `/metrics`: Prometheus exposition

### 3-2. 요청 경계

- `X-Request-ID`와 `X-AIQA-Run-ID`는 영문자·숫자로 시작하고 이후에는
  영문자, 숫자, `.`, `_`, `-`만 사용하며 최대 64자입니다.
- 유효하지 않은 `X-Request-ID`는 서버가 만든 UUID로 교체하고, 유효하지 않은
  `X-AIQA-Run-ID`는 telemetry context에서 제외합니다.
- 이 헤더는 로그와 trace를 연결하는 correlation 값일 뿐입니다. 사용자나
  서비스의 신원을 증명하는 인증 정보로 사용하지 않습니다.
- `/v1/predict`의 요청 본문은 `configs/serving/api.yaml`의
  `max_request_body_bytes`를 넘을 수 없습니다. 기본 제한은 65,536바이트이며,
  초과하면 본문을 파싱하거나 기록하지 않고 `413 REQUEST_BODY_TOO_LARGE`를
  반환합니다.
- 성공 응답에도 항상 설정의 `education_only` 값을 포함합니다. 이 저장소의
  기본값은 `true`이며, 결과를 임상 판단이나 환자 처치에 재사용할 수 있다는
  의미가 아닙니다.

## 4. Trace와 metric 경계

`/v1/predict`는 FastAPI HTTP SERVER span 아래에서 `risk.predict` operation을
수행합니다. Kubernetes에서 KServe backend를 선택하면 이 operation 안에서
`kserve.infer` CLIENT span을 열고, 그 span의 W3C context와 request ID를 KServe로
전달합니다.

- `/v1/predict`만 Risk API의 business metric 대상입니다. `/health/*`와 `/metrics`는 business metric을 만들지 않고 trace도 남기지 않습니다.
- 요청 수와 지연, 예측 지표는 허용된 scenario로만 구분합니다. 알 수 없는 값은
  `other`로 묶습니다.
- 입력 규약 오류 422는 `error_code=MODEL_INPUT_INVALID`와
  `validation_category=missing|extra|type|other`만 log와 span에 남깁니다. 입력값과
  내부 오류 원문은 복사하지 않습니다.
- 본문 크기 오류 413은 `error_code=REQUEST_BODY_TOO_LARGE`와
  `rejection_category=body_too_large`만 log와 span에 남깁니다.
- `trace_id`는 JSON log와 trace 탐색을 연결할 때만 사용합니다. request ID, run ID, trace ID, span ID는 Prometheus metric label이 아닙니다.
