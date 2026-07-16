# 4장 Observability

## 1. 목표와 evidence scope

각 수강생의 Grafana Cloud stack으로 Risk API logs, metrics와 traces를 보내고
repository dashboard를 고정 UID로 import합니다. Grafana, Loki, Tempo와 Prometheus
server를 VM에 설치하지 않습니다.

이 Lab의 목표는 chart를 열었다고 release answer를 만드는 것이 아닙니다. dashboard
query, traffic scenario, identity와 time window를 연결해 **어떤 input/API/runtime
candidate가 강화됐는지** 기록합니다. label 없는 operational signal만으로 Candidate B의
Recall·Precision·FN이나 model defect를 확정하지 않습니다.

Grafana credential, Alloy secret 또는 Docker가 없으면 Notebook static contract를
확인하고 `Grafana live evidence not observed` 또는 `target_pending`으로 남깁니다.
dashboard URL·screenshot·ingestion success를 실제로 보지 않았는데 완료라고 쓰지
않습니다.

## 2. 사전 설정

### 2-1. Alloy Secret

`deploy/compose/simple-mlops/secrets/alloy/README.md`에 따라 일곱 개 파일을 만듭니다.
Alloy write token과 Dashboard API token은 분리합니다.

### 2-2. Dashboard 설정

```bash
cp .env.grafanacloud.example .env.grafanacloud
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard --check
```

개인 Grafana URL, Dashboard API token, folder UID와 metrics/logs/traces datasource UID를
`.env.grafanacloud`에 입력합니다. 실제 값은 Git에 추가하지 않습니다. `--check`가
missing setting을 알려 주면 이는 expected setup blocker이며 import success가 아닙니다.

## 3. Dashboard contract와 live traffic

### 3-1. Notebook static check

`01_inspect_dashboard_contract.ipynb`는 dashboard UID `tta-aiqa-quality`, five
app-owned `aiqa_risk_*` metrics, Prometheus/Loki/Tempo datasource와 local `/metrics`
fallback을 확인합니다. static pass는 Grafana Cloud ingestion pass가 아닙니다.

### 3-2. Alloy 연결, traffic, dashboard import

Docker/Alloy와 개인 Grafana Cloud configuration이 준비된 경우에만 실행합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d --build
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator current-shift --count 20
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator invalid --count 3
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

출력된 dashboard URL을 열고 environment/model profile/version/scenario, time window,
request status mix, P95 latency, score/prediction/missing-feature signal과 representative
request ID를 capture합니다. 다시 실행해도 UID `tta-aiqa-quality`의 같은 dashboard가
갱신되어야 합니다.

`invalid` traffic은 HTTP 422 feature-contract violation을 의도적으로 만듭니다. 422는
Request rate의 status-code series에서 확인하고, Error rate panel은 5xx만 계산합니다.
따라서 5xx panel에 422가 없다는 사실을 “validation failure가 없었다”로 해석하지
않습니다.

## 4. 제출물과 cleanup

다음을 한 행으로 제출합니다.

> [environment] [time window]에서 [model profile/version/scenario]의
> [status/latency/score/prediction/missing-feature] signal을 [dashboard URL 또는 API
> metrics]에서 확인했다. 이 signal은 [input/API/runtime candidate]를 강화하지만
> target label-based model metric과 root cause는 아직 확정하지 않는다. [owner]가
> [required evidence]를 수집하면 release record의 operational recommendation을
> 재평가한다.

본인이 시작했고 다음 Lab에 필요하지 않은 Compose workload만 정리합니다. 다른
수강생 또는 강사가 이미 시작한 workload는 정리하지 않습니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down
```
