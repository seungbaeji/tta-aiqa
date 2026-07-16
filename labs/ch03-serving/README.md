# 3장 Serving

## 1. 목표와 evidence scope

Compose에서는 local sklearn adapter를, Kubernetes에서는 KServe HTTP adapter를
사용하지만 외부 Risk API 계약은 동일해야 합니다. 이 Lab은 “API가 응답한다”가 아니라
**실제로 확인한 runtime identity가 approved artifact와 맞는지**를 scope와 함께
기록하는 연습입니다.

| scope | 이 Lab에서 확인할 수 있는 evidence | 아직 말할 수 없는 것 |
| --- | --- | --- |
| `prepared` | published bundle, rendered manifest, static Notebook check | target cluster가 실행 중임 |
| `local_verified` | local Compose의 `/health/ready`, `/v1/model`, 200/422 | target runtime도 같은 상태임 |
| `target_pending` | Docker/kubectl/target URL이 없어 live result를 보지 못한 상태 | deployment success 또는 failure |

Candidate B의 frozen model `APPROVE`는 2장의 offline evidence입니다. 이 Lab에서
target identity를 관측하지 못했다고 이를 `HOLD`로 바꾸지 않습니다.

## 2. Local selected bundle과 Compose 실행

### 2-1. Baseline bundle 준비

```bash
uv run python scripts/publish_model.py baseline --revision v2
cat artifacts/models/revisions/v2/deployed/deployment.json
```

`deployment.json`의 profile과 model SHA-256은 local mount가 읽을 bundle을 가리키는
`prepared` evidence입니다. 현재 baseline expected model hash는 `f2576f12512a...`이며,
target deployment success를 뜻하지는 않습니다.

이 baseline Lab은 rollback-safe public API contract를 연습하기 위한 local profile입니다.
local baseline 200/422를 Candidate B target runtime evidence로 바꾸지 않습니다. Candidate
B overlay는 static desired state로 먼저 대조하고, target identity/time window는 GitOps
sequence가 허용한 실제 observation에서만 report합니다.

### 2-2. Local API contract

```bash
uv run python scripts/publish_model.py baseline --revision v2
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --build risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
```

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator invalid --count 3
```

baseline traffic은 HTTP 200, intentional feature-contract violation은 HTTP 422
`MODEL_INPUT_INVALID`을 기록해야 합니다. `/v1/model`의 profile/version/threshold와
response의 `X-Request-ID`도 함께 capture합니다. request ID는 response·log·trace
correlation용이며 Prometheus metric label이 아닙니다. response artifact는
`artifacts/traffic/` 아래에 생성됩니다.

Docker command가 없거나 API가 시작하지 않으면 다음 Notebook의 static section만
실행하고 `prepared` 또는 `target_pending`으로 기록합니다. 없는 live response를
재현한 것처럼 적지 않습니다.

### 2-3. Notebook

`01_verify_risk_api.ipynb`는 V2 operational pool의 target-free 133-feature payload와
KServe static contract를 검사합니다. API가 다른 local URL에 있으면
`AIQA_RISK_API_URL`을 설정합니다. `API_NOT_RUNNING`은 static check가 실패했다는
뜻이 아니라 live API evidence의 blocker와 next action입니다.

## 3. Kubernetes desired state 확인

```bash
kubectl config current-context
kubectl kustomize deploy/kubernetes/overlays/baseline >/tmp/tta-aiqa-baseline.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-baseline.yaml
```

실제 Argo CD sync 절차와 개인 URL은 강사가 안내합니다. 수강생은 direct apply로
release를 바꾸지 않습니다. Rendered `model-identity` ConfigMap의
`AIQA_KSERVE_EXPECTED_MODEL_SHA256`과 baseline PVC subPath의 bundle digest가 같은지도
확인합니다. 두 값이 다르면 predictor startup integration contract가 실패해야 합니다.
`ghcr-pull`은 강사가 namespace에 미리 준비하는 registry Secret이며 수강생의 Grafana
Cloud Secret과 별개입니다. `kubectl` 또는 target context가 없으면 rendered/static
manifest evidence까지만 남기고 `target_pending`으로 기록합니다.

`kubectl`이 없는 환경에서는 Candidate B overlay와 rollback path의 static contract를
다음 test로 확인합니다.

```bash
uv run pytest -q tests/integration/deployment/test_kubernetes_contract.py \
  -k candidate_and_rollback_overlays_select_only_approved_models
```

이 결과는 `candidate-b-c712a8e52344` immutable path가 desired state에 선언됐다는
evidence일 뿐 Candidate B target API observation은 아닙니다.

## 4. 제출물과 다음 gate

다음을 한 행으로 제출합니다.

> operational deployment scope는 [prepared/local_verified/target_pending]이다.
> [artifact/API/manifest]에서 [profile, version 또는 digest]를 확인했고,
> valid/invalid contract는 [실행 결과 또는 blocker]로 기록했다. Candidate B의 frozen
> `APPROVE`는 유지하되 [target identity/traffic window]는 [owner]가 확인할 때까지
> operational conclusion으로 확장하지 않는다.

4장에서는 같은 API identity를 전제로 traffic scenario와 telemetry가 input/API/runtime
candidate 중 무엇을 강화하는지 조사합니다.
