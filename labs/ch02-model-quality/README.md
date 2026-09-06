# 2장 모델 품질

이 장은 9단계 여정의 **모델** 단계입니다. 데이터 단계의 split과 품질 범위를
이어받아 공식 후보 판단과 lineage를 분리합니다.

## 모델

### Precision·Recall·F1·FP/FN과 PR-AUC를 같은 release 질문으로 해석한다

`00_train_valid_model_walkthrough.ipynb`를 실행하기 전에 accuracy 하나로
판단할 때 생길 오류를 예측합니다. 노트북은 `train` 2,900건과 `valid` 600건만
사용하며, 개발용 결과의 정확도 0.8550, 재현율 0.2169, FN 65를 Candidate
공식 결과와 섞지 않습니다. Precision, Recall, F1, FP/FN, AUROC와 PR-AUC가
어떤 보호 질문에 답하는지 기록합니다.

### Candidate A는 HOLD이고 Candidate B는 APPROVE인지 canonical benchmark로 판정한다

다음 명령으로 고정된 모델 상태를 확인합니다.

```bash
uv run python scripts/run_model.py status --revision v2
```

`docs/reference/evidence/model/revisions/v2/canonical-benchmark.json`과
`release-manifest.json`에서 Candidate A `HOLD`, Candidate B `APPROVE`를
모델 승인으로 기록합니다. B의 승인은 대상 배포 완료가 아니며, sealed test에
맞춰 특성·임계값·release policy를 바꾸지 않습니다.

`01_compare_model_evidence.ipynb`를 위에서 아래로 실행하면 특성, profile, 정책,
PR-AUC, precision, recall, FN과 보호 기준의 연결을 같은 범위에서 읽을 수 있습니다.

### DVC revision과 MLflow run이 같은 model evidence lineage를 가리키는지 확인한다

`model-bootstrap.json`, `release-freeze.json`, `canonical-benchmark.json`,
`release-manifest.json`의 순서와 DVC revision, dataset digest, MLflow run을
대조합니다. MLflow 화면이 없으면 JSON evidence를 읽고 화면 미확인을 별도로
기록합니다. 필요할 때만 같은 Compose의 MLflow service를 시작합니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d mlflow
curl http://127.0.0.1:5000/health
```

## 단계 완료

E-03에 후보별 판단, 사용한 canonical 경로와 lineage의 확인 범위를 남깁니다.
다음 **API** 단계에서는 이 모델 승인을 운영 배포 완료로 확대하지 않고 실제
serving metadata를 별도로 대조합니다.
