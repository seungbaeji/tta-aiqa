# Chapter 03 Serving Inspection Evidence

이 파일은 Docker daemon, MLflow server, Kubernetes cluster를 사용할 수 없는 수강생이 3장 보고서에 남길 수 있는 prepared inspection 근거입니다. 이 내용은 live 실행 결과가 아니라 파일과 prepared artifact 기준 확인 결과입니다.

## Container Files

| 항목 | 확인값 | QA 해석 |
| --- | --- | --- |
| Dockerfile | `demos/ch03_docker_kubernetes/Dockerfile` | 모델 serving 코드를 같은 실행 환경으로 묶는 파일입니다 |
| compose | `compose.yaml`, `jupyterlite/files/artifacts/deployment/chapter_03/compose.yaml` | API와 MLflow server를 함께 띄우는 로컬 확인 경로입니다 |
| 실행 스크립트 | `check_container.sh` | container smoke test를 실행할 수 있는 선택 경로입니다 |

Container file inspection만으로는 `/health`, `/predict`, latency, telemetry가 실제로 확인됐다고 말할 수 없습니다. 실행하지 않았다면 “컨테이너 실행 파일 구조를 확인했습니다”라고만 기록합니다.

## MLflow Candidate

| 항목 | 확인값 | QA 해석 |
| --- | --- | --- |
| 평가 기록 | `artifacts/experiments/chapter_02/model_test_eval.json` | 2장에서 계산한 dataset, model version, threshold, metric 조건입니다 |
| Registered model URI | `models:/risk-classifier@candidate` | serving 후보 모델을 registry alias로 부르는 주소입니다 |
| KServe annotation | `ai-quality/mlflow-model-uri: models:/risk-classifier@candidate` | serving manifest가 어떤 MLflow 후보를 설명하는지 남깁니다 |
| model storage | `pvc://ai-quality-models/risk-classifier/candidate` | KServe runtime이 읽을 model artifact 위치입니다 |

MLflow candidate 확인은 “어떤 모델을 배포하려는가”에 답합니다. 하지만 MLflow URI가 있다고 해서 Argo CD sync, KServe Ready, endpoint 응답이 확인된 것은 아닙니다.

## Argo CD And KServe

| 항목 | 확인값 | QA 해석 |
| --- | --- | --- |
| Argo CD Application | `demos/ch03_docker_kubernetes/argocd/application.yaml` | GitOps sync가 바라볼 repository, revision, path를 선언합니다 |
| GitOps path | `demos/ch03_docker_kubernetes/argocd-resources/overlays/student` | Kustomize overlay를 통해 MLflow/KServe resource를 Argo CD가 반영할 경로입니다 |
| MLflow ingress patch | `demos/ch03_docker_kubernetes/argocd-resources/overlays/student/ingress-host-patch.yaml` | 수강생 환경에 맞게 MLflow UI host를 수정해야 하는 파일입니다 |
| KServe resource | `InferenceService/ai-quality-risk-classifier` | candidate model을 endpoint resource로 선언합니다 |
| runtime hint | `predictor.sklearn`, `protocolVersion: v2` | Tree 기반 scikit-learn 모델을 KServe runtime 계층에서 serving하려는 구조입니다 |
| observability contract | `request_id,model_version,score,threshold,prediction,latency_ms,validation_failure` | 4장에서 로그와 metric으로 이어질 필드 계약입니다 |

KServe manifest inspection만으로는 실제 runtime container가 생성되었는지, model storage 접근이 성공했는지, endpoint response가 계약을 만족했는지 검증했다고 말할 수 없습니다. live cluster가 없으면 이 항목은 `unverified`로 남깁니다.

## Report Boundary

보고서에는 다음처럼 씁니다.

```text
3장에서는 container file, MLflow candidate URI, Argo CD Application, KServe InferenceService를 파일 기준으로 확인했습니다.
`models:/risk-classifier@candidate`는 2장 평가 기록과 연결되는 serving 후보 URI이며, KServe manifest의 annotation과 storageUri에 배포 후보 단서가 남아 있습니다.
다만 Argo CD live sync, KServe Ready, endpoint response, telemetry field는 현재 환경에서 직접 확인하지 않았으므로 미검증 상태로 4장 운영 관측 확인에 넘깁니다.
```
