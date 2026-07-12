# 5장 Release Decision

## 1. 목표

### 1-1. 조건부 배포

Candidate A는 보류하고 Candidate B만 배포한 뒤 같은 Risk API URL과 dashboard에서
변경을 확인합니다. 마지막에는 baseline rollback을 검증합니다.

## 2. 판단 확인

### 2-1. Evidence

```bash
uv run python scripts/run_model.py status --revision v2
```

`reference/evidence/model/revisions/v2/release-manifest.json`은 canonical decision,
sealed-test final benchmark, bundle digest와 approved Candidate B MLflow run을 연결합니다.

### 2-2. Notebook

`01_review_release_decision.ipynb`에서 canonical decision, release manifest와
Kubernetes overlay를 연결합니다. Candidate A는 어떤 overlay에도 포함되지 않아야 합니다.

## 3. Candidate B 배포

### 3-1. Immutable publish

강사 환경에서 model host path가 준비된 상태로 실행합니다.

```bash
uv run python scripts/publish_model.py candidate-b \
  --revision v2 \
  --target-root /mnt/course-models
```

### 3-2. GitOps manifest

```bash
kubectl config current-context
kubectl kustomize deploy/kubernetes/overlays/candidate-b >/tmp/tta-aiqa-candidate-b.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-candidate-b.yaml
```

강사가 안내한 branch와 Argo CD 절차로 Candidate B overlay를 sync합니다. `/v1/model`에서
Candidate B version을 확인하고 `approved-candidate` traffic을 보냅니다. Overlay는 PVC
subPath와 `model-identity` ConfigMap의 expected model digest를 함께 Candidate B bundle로
전환해야 합니다.

## 4. 운영 증거와 Rollback

### 4-1. 누적 확인

같은 Grafana dashboard에서 baseline과 Candidate B `model_version`이 시간 순서로 모두
조회되는지 확인합니다. current-shift와 invalid traffic은 input/API 품질 신호이며
Candidate B 자체 결함으로 단정하지 않습니다.

### 4-2. Baseline 복구

```bash
kubectl kustomize deploy/kubernetes/overlays/rollback >/tmp/tta-aiqa-rollback.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-rollback.yaml
```

rollback sync 후 `/health/ready`와 `/v1/model`이 baseline version으로 복구되어야 합니다.

## 5. 완료 기준

### 5-1. Release 기록

- Candidate A `HOLD`, Candidate B `APPROVE` 근거와 release-manifest의 artifact hash를 설명합니다.
- Rendered KServe predictor의 expected model digest가 선택된 PVC bundle과 일치함을 확인합니다.
- Candidate B 배포 전후 API와 telemetry evidence를 남깁니다.
- rollback 후 baseline 복구를 확인하고, 확인하지 못한 external scope를 release 기록에 남깁니다.
