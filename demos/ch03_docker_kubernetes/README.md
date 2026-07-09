# Chapter 3 Docker and Kubernetes Demo

이 Demo는 모델 파일, 실행 환경, 설정값이 하나의 배포 단위로 묶이는 방식을 보여줍니다. 수강생은 Dockerfile과 Kubernetes Manifest를 작성하지 않고, 제공된 파일에서 image, port, environment, readiness, threshold, model_version을 확인합니다.

```bash
docker compose --profile serving up --build serving-api
bash demos/ch03_docker_kubernetes/scripts/check_container.sh
```

Kubernetes 파일은 `demos/ch03_docker_kubernetes/k8s` 아래에 있습니다. 실습 환경에 Kubernetes가 없으면 Manifest를 읽고 확인 포인트만 리뷰합니다.

Docker daemon이나 Kubernetes cluster 권한이 없으면 실행 실패를 수강생 실패로 처리하지 않습니다. 이 경우 `Dockerfile`, `scripts`, `k8s` manifest를 읽고 `artifacts/reports/chapter_03_serving_inspection.md`의 prepared inspection 근거와 비교합니다. 보고서에는 live smoke test 미실행과 inspection 기준 확인을 분리해서 남깁니다.

## Argo CD GitOps repository 연결

Argo CD가 이 repository를 읽으려면 GitHub Deploy key를 read-only로 등록합니다. GitHub에는 public key를 등록하고, Argo CD에는 private key를 repository credential로 등록합니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/setup_argocd_gitops.sh key
```

출력된 public key를 GitHub repository의 `Settings -> Deploy keys -> Add deploy key`에 등록합니다. `Allow write access`는 체크하지 않습니다.

GitHub 등록이 끝나면 Argo CD에 private key를 등록합니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/setup_argocd_gitops.sh connect
```

그 다음 Argo CD `Application`을 등록하고 sync를 확인합니다.

```bash
export ARGOCD_REPO_URL=git@github.com:seungbaeji/tta-aiqa.git
bash demos/ch03_docker_kubernetes/scripts/setup_argocd_gitops.sh sync
```
