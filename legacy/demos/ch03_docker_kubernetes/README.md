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

Argo CD가 바라볼 배포 파일은 `gitops/overlays/tta` 아래에 있습니다. 이 overlay는 base의 MLflow tracking `Deployment`/`Service`/PVC와 KServe `InferenceService`를 함께 렌더링합니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/02_check_argocd_manifests.sh
```

이 명령은 Kustomize render와 선택적 client dry-run을 수행합니다. Kubernetes나 KServe가 준비되지 않은 교육장에서는 이 결과를 배포 파일 확인 근거로 사용합니다. 이 경우 실제 배포 성공이 아니라 “MLflow와 KServe 배포 선언을 확인했다”로 기록합니다.

`gitops/base`는 공통 배포 resource입니다. 수강생은 이 폴더를 직접 고치기보다 `gitops/overlays/tta` 아래의 수업용 overlay를 확인합니다. MLflow ingress host는 cluster 내부 라우팅 선언을 검토하기 위한 값이며, 수강생이 브라우저에서 여는 주소는 Bastion tunnel의 `http://localhost:5000`입니다. 강사가 별도 ingress host를 배정한 경우에만 다음 파일의 placeholder를 수정합니다.

```yaml
# gitops/overlays/tta/ingress-host-patch.yaml
- op: replace
  path: /spec/rules/0/host
  value: mlflow.REPLACE_WITH_YOUR_INGRESS_DOMAIN.example.com
```

강사가 별도 ingress host를 배정했다면 `value`를 그 값으로 바꿉니다. 별도 ingress 주소가 없으면 placeholder를 둔 채 manifest inspection 또는 live sync resource 상태 확인까지만 진행하고, UI 확인은 Bastion tunnel로 `http://localhost:5000`을 열어 기록합니다.

## UI 확인 경로

UI 확인은 VM에서 service를 실행한 뒤 Windows PC의 Bastion tunnel로 접근합니다. 이 Demo에서 local smoke path나 MLflow container를 실행한 뒤에는 별도 PowerShell 또는 Windows Terminal에서 tunnel을 유지하고, 브라우저는 Windows PC의 `localhost` 주소를 엽니다.

```bash
ssh -N \
  -L 5000:127.0.0.1:5000 \
  -L 8000:127.0.0.1:8000 \
  -L 3000:127.0.0.1:3000 \
  -J mrml-bastion@146.56.41.109 \
  tta@10.99.0.20
```

| UI | Windows PC 브라우저 주소 | 먼저 VM에서 실행할 것 |
| --- | --- | --- |
| MLflow | `http://localhost:5000` | `docker compose up -d mlflow` 또는 MLflow 포함 script |
| FastAPI docs | `http://localhost:8000/docs` | `docker compose --profile serving up --build serving-api` |
| Grafana | `http://localhost:3000` | `docker compose up -d loki grafana` |
| Argo CD | `https://gitops.lab.mrml.dev` | Argo CD `Application` 등록 또는 조회 |

## Argo CD live sync path

Argo CD와 KServe가 준비된 클러스터에서는 Git repository를 Argo CD에 먼저 연결해야 합니다. 이 단계는 두 가지 작업으로 나뉩니다.

| 단계 | 하는 일 | 왜 필요한가 |
| --- | --- | --- |
| Repository credential 등록 | Argo CD가 GitHub repository를 읽을 수 있게 SSH deploy key를 등록 | private repository나 인증이 필요한 repository를 읽기 위해 필요 |
| Application 등록 | Argo CD가 어떤 repo, branch, path를 cluster에 맞출지 선언 | `gitops/overlays/tta`를 desired state로 삼기 위해 필요 |

처음 live sync를 할 때는 아래 순서로 진행합니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh check
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh key
```

`key` 명령은 public key를 출력합니다. 이 public key를 GitHub repository의 `Settings -> Deploy keys -> Add deploy key`에 붙여 넣습니다. `Allow write access`는 체크하지 않습니다. Argo CD는 이 repository를 읽기만 하면 됩니다.

아래 명령어로 키 생성
```
ssh-keygen -t ed25519 -C "argocd-tta-aiqa" -f ./tta-aiqa-argocd-deploy-key -N ""
```

github에는 public key 등록


그 다음 Argo CD에 repository credential과 Application을 등록합니다.

```bash
ARGOCD_REPO_URL=git@github.com:<your-org-or-user>/<your-repo>.git \
  bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh connect
```

`connect`는 내부적으로 `argocd repo add ... --ssh-private-key-path ...`를 실행해 repository credential을 등록하고, `argocd/application.yaml`의 `repoURL` placeholder를 실제 repository URL로 바꾼 임시 Application manifest를 `kubectl apply`합니다.

Application 등록 후 sync합니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh sync
bash demos/ch03_docker_kubernetes/scripts/05_check_kserve_endpoint.sh
```

sync 순서는 manifest annotation 기준으로 MLflow tracking resource가 먼저, MLflow ingress가 그 다음, KServe `InferenceService`가 마지막입니다. live sync가 불가능하면 실패를 수강생 실패로 처리하지 않습니다. 보고서에는 `Application` manifest, Git path, KServe `InferenceService`, `storageUri`는 확인했지만 Argo CD sync, KServe readiness, endpoint response는 미검증이라고 분리해서 남깁니다.

## 확인 경로

| 경로 | 역할 |
| --- | --- |
| `argocd/application.yaml` | Argo CD `Application` template |
| `gitops/base/mlflow-tracking.yaml` | MLflow tracking `Deployment`, `Service`, model artifact PVC |
| `gitops/base/mlflow-ingress.yaml` | MLflow ingress 선언 확인용 기본 resource |
| `gitops/base/inferenceservice.yaml` | KServe candidate serving 선언 |
| `gitops/overlays/tta/kustomization.yaml` | TTA 실습용 overlay |
| `gitops/overlays/tta/ingress-host-patch.yaml` | 강사가 별도 배정한 경우에만 수정할 ingress host patch |
| `scripts/00_setup_argocd_gitops.sh` | deploy key 생성, repo credential 등록, Application 등록, sync wrapper |
| `scripts/02_check_argocd_manifests.sh` | Kustomize render와 선택적 dry-run |
| `scripts/01_check_container.sh` | Docker Compose local smoke 확인 |
| `scripts/04_sync_argocd_application.sh` | Argo CD diff, sync, wait |
| `scripts/05_check_kserve_endpoint.sh` | KServe `InferenceService` status 확인 |
