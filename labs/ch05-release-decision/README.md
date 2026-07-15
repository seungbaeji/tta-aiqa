# 5장 Release Decision

## 1. 목표와 두 판단 gate

이 Lab은 Candidate B를 무조건 target에 배포하는 실습이 아닙니다. Candidate A=`HOLD`,
Candidate B=`APPROVE`라는 frozen model evidence와 실제 runtime/telemetry observation을
한 release record에 함께 적습니다. target cluster 또는 Grafana Cloud를 보지 못한 경우
Candidate B model approval을 바꾸지 않고 `operational_deployment_scope=target_pending`으로
남깁니다.

| field | 이 Lab의 현재 public evidence | target을 직접 관측해야 추가할 evidence |
| --- | --- | --- |
| model approval | A=`HOLD`, B=`APPROVE`, `deployment_allowed=true` | 새로운 frozen revision이 없으면 변경하지 않음 |
| operational scope | manifest/overlay static check, local Notebook fallback | GitOps sync, target API identity, traffic/telemetry time window |
| current recommendation | `target evidence collection` | observed scope에 맞는 controlled rollout 또는 rollback review |

## 2. Frozen release chain과 Notebook

```bash
uv run python scripts/run_model.py status --revision v2
uv run pytest -q \
  tests/integration/qa/test_v2_serialized_bundle_verification.py \
  tests/integration/deployment/test_kubernetes_contract.py
```

`docs/reference/evidence/model/revisions/v2/release-manifest.json`은 canonical decision,
sealed-test final benchmark, pre-test freeze, bundle digest와 approved Candidate B MLflow run을
연결합니다. frozen evidence를 다시 만들거나 sealed test를 tuning에 사용하지 않습니다.

`01_review_release_decision.ipynb`는 canonical decision, release manifest, baseline,
Candidate B와 rollback overlay를 대조합니다. URL이 없다면 `URL_NOT_CONFIGURED`와
`target_pending`이 expected fallback입니다. Candidate A는 어떤 overlay에도 포함되지 않아야
합니다.

## 3. Candidate B immutable publish와 GitOps target gate

강사 환경에서 model mount path가 준비된 경우에만 immutable publish를 실행합니다.

```bash
uv run python scripts/publish_model.py candidate-b \
  --revision v2 \
  --target-root /mnt/course-models
```

output path의 `candidate-b-c712a8e52344`와 `deployment.json` profile/model SHA-256을
capture합니다. 이 결과는 selected bundle의 prepared evidence이며, target PVC mount,
KServe startup이나 Risk API availability를 뜻하지 않습니다.

강사 제공 target context에서는 manifest shape만 먼저 검사합니다.

```bash
kubectl config current-context
kubectl kustomize deploy/kubernetes/overlays/candidate-b >/tmp/tta-aiqa-candidate-b.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-candidate-b.yaml
```

actual Candidate B sync는 강사가 안내한 GitOps/Argo CD workflow에서만 수행합니다.
`AIQA_EXPECTED_PROFILE=candidate-b`를 명시한 뒤 target `/v1/model`, valid contract
response, scenario, dashboard URL과 telemetry time window를 capture합니다. API profile 하나나
HTTP 200 하나만으로 `target_verified`라고 쓰지 않습니다.

## 4. Rollback review와 failure path

rollback overlay는 baseline immutable path를 선언하는 desired state입니다.

```bash
kubectl kustomize deploy/kubernetes/overlays/rollback >/tmp/tta-aiqa-rollback.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-rollback.yaml
```

expected Candidate B identity mismatch, valid payload contract failure, 또는 owner가 검증한
live operational condition은 `rollback_required` review를 열 수 있습니다. intentional
invalid traffic 422는 input validation route이며 5xx Error rate, model defect 또는 automatic
rollback trigger로 바꾸지 않습니다.

actual rollback sync 후 baseline API identity, traffic과 telemetry를 새 time window에서
관측해야 recovery를 report할 수 있습니다. target context가 없으면 static overlay와 required
owner evidence만 남깁니다.

## 5. 제출물

> Candidate A는 frozen V2 policy에서 `HOLD`, Candidate B는 `APPROVE`다. release manifest와
> Candidate B overlay의 immutable identity는 [static/observed scope]로 확인했지만,
> [target GitOps/API identity/telemetry]는 [observed 또는 pending]이다. 따라서 operational
> deployment scope는 [prepared/local_verified/target_verified/target_pending/rollback_required],
> current recommendation은 [target evidence collection/controlled rollout/rollback review]이며
> [owner]가 [next evidence]를 수집한 뒤 재평가한다.
