# 2장 모델 품질

## 1. 목표

### 1-1. Evidence-based decision

Baseline, Candidate A와 Candidate B를 같은 sealed test 기준으로 비교하고 단일
metric이 아니라 release guardrail 전체로 판단합니다. 모델 개발과 tuning 과정은
이 실습 범위가 아닙니다.

## 2. 실행

### 2-1. Canonical 상태

```bash
uv run python scripts/run_model.py status --revision v2
```

Candidate A `HOLD`, Candidate B `APPROVE`가 출력되어야 합니다. 이 결과는
`release-manifest.json`으로 publication authorization까지 연결됩니다.
`deployment_allowed: true`는 frozen model evidence에서 Candidate B publication 또는
controlled rollout을 허용하는 값이며, target Kubernetes가 이미 Candidate B bundle을
실행하거나 Grafana Cloud telemetry가 정상이라는 뜻은 아닙니다. 그 operational
deployment 판단은 3~5장에서 API identity와 external runtime evidence로 별도 기록합니다.

### 2-2. Evidence lifecycle

같은 V2 evidence directory 안에서도 lifecycle 시점은 다릅니다.

1. `model-bootstrap.json`은 sealed test 전 train/valid bundle과 MLflow run을 기록하며
   candidate의 initial `deployed: false` state를 보입니다.
2. `release-freeze.json`은 test 전 policy와 bundle hash를 동결합니다.
3. `final-benchmark.json`과 `canonical-benchmark.json`은 one-shot sealed test result와
   A=`HOLD`, B=`APPROVE`를 기록합니다.
4. `release-manifest.json`은 approved Candidate B bundle, canonical/final/freeze digest와
   provenance를 publication authorization으로 bind합니다.

따라서 bootstrap의 pre-test deployment state로 final canonical model approval을
덮어쓰거나, final approval만으로 target deployment 완료를 선언하지 않습니다.

### 2-3. Notebook

VS Code에서 `01_compare_model_evidence.ipynb`를 열어 위에서 아래로 실행합니다.
Notebook은 feature/profile/policy configuration, PR-AUC, Precision, Recall, FN,
bootstrap lower bound와 각 guardrail 결과를 연결합니다.

### 2-4. MLflow

Compose의 MLflow service를 시작합니다. 3장에서도 같은 service를 사용하므로
별도 local MLflow server를 실행하지 않습니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d mlflow
curl http://127.0.0.1:5000/health
```

VS Code port forwarding 또는 강사가 제공한 URL로 UI를 엽니다. 세 profile의
parameter, validation metric, dataset lineage와 MLflow run ID를 확인합니다.

## 3. 완료 기준

### 3-1. 판단

- Candidate A가 recall, uncertainty, false-negative guardrail 중 무엇을 통과하지
  못했는지 설명합니다.
- Candidate B가 Recall과 FN을 개선하면서 Precision floor와 PR-AUC 기준을 지켰는지
  확인합니다.
- sealed test 결과를 보고 feature, threshold 또는 release policy를 변경하지 않습니다.
- ML Engineer와 MLOps 담당자는 feature/profile/policy hash와 MLflow run이 서로
  다른 책임을 가진다는 점을 설명합니다.
- QA report에는 Candidate B의 `APPROVE`를 model approval으로 기록하고, actual
  local/target runtime identity는 확인한 scope만 별도 field에 씁니다.
