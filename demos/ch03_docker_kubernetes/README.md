# Chapter 3 Container, MLflow, Kubernetes Deployment Demo

이 Demo는 container smoke test에서 시작해, Kubernetes에 MLflow tracking service를 먼저 배포하고, 그 뒤 `risk-classifier@candidate` 모델을 KServe endpoint 후보로 연결하는 경로를 보여줍니다. 기본 배포 경로는 `kubectl apply`로 KServe manifest를 직접 적용하는 방식이 아니라, Git에 있는 MLflow/KServe manifest를 Argo CD `Application`이 sync하는 방식입니다.

## Local smoke path

Docker는 local smoke test와 custom predictor 실행 환경 확인에 사용합니다.

```bash
docker compose --profile serving up --build serving-api
bash demos/ch03_docker_kubernetes/scripts/01_check_container.sh
docker compose --profile serving down
```

## Kubernetes 배포 파일 확인 경로

Argo CD가 바라볼 배포 파일은 `gitops/overlays/dev` 아래에 있습니다. 이 overlay는 base의 MLflow tracking `Deployment`/`Service`/PVC와 KServe `InferenceService`를 함께 렌더링합니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/02_check_argocd_manifests.sh
```

이 명령은 Kustomize render와 선택적 client dry-run을 수행합니다. Kubernetes나 KServe가 준비되지 않은 교육장에서는 이 결과를 배포 파일 확인 근거로 사용합니다. 이 경우 실제 배포 성공이 아니라 “MLflow와 KServe 배포 선언을 확인했다”로 기록합니다.

## Argo CD live sync path

Argo CD와 KServe가 준비된 클러스터에서는 먼저 `argocd/application.yaml`의 `repoURL`을 실제 repository로 바꾼 뒤 Application을 등록하고 sync합니다. sync 순서는 manifest annotation 기준으로 MLflow tracking resource가 먼저, KServe `InferenceService`가 다음입니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/03_register_argocd_application.sh
bash demos/ch03_docker_kubernetes/scripts/04_sync_argocd_application.sh
bash demos/ch03_docker_kubernetes/scripts/05_check_kserve_endpoint.sh
```

live sync가 불가능하면 실패를 수강생 실패로 처리하지 않습니다. 보고서에는 `Application` manifest, Git path, KServe `InferenceService`, `storageUri`는 확인했지만 Argo CD sync, KServe readiness, endpoint response는 미검증이라고 분리해서 남깁니다.

## 확인 경로

| 경로 | 역할 |
| --- | --- |
| `argocd/application.yaml` | Argo CD `Application` template |
| `gitops/base/mlflow-tracking.yaml` | MLflow tracking `Deployment`, `Service`, model artifact PVC |
| `gitops/base/inferenceservice.yaml` | KServe candidate serving 선언 |
| `gitops/overlays/dev/kustomization.yaml` | 수업용 dev overlay |
| `scripts/02_check_argocd_manifests.sh` | Kustomize render와 선택적 dry-run |
| `scripts/01_check_container.sh` | Docker Compose local smoke 확인 |
| `scripts/04_sync_argocd_application.sh` | Argo CD diff, sync, wait |
| `scripts/05_check_kserve_endpoint.sh` | KServe `InferenceService` status 확인 |
