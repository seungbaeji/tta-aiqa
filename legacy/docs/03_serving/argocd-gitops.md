# 3-6. Argo CD GitOps 배포 흐름

이 문서는 `ttamlops-2607` 강의 자료의 GitOps 설명을 `tta-aiqa` 수강생 실습 경로에 맞게 옮긴 자료입니다. 판단 질문은 후보 모델을 Kubernetes에 직접 `kubectl apply`로 올리는 것이 아니라, Git에 있는 배포 파일을 Argo CD가 읽고 cluster 상태와 맞출 수 있는가입니다.

이 실습에서 수강생은 Argo CD 운영자가 되는 것이 아닙니다. 확인할 것은 어떤 Git 경로가 배포 기준인지, Argo CD가 어느 namespace에 어떤 resource를 동기화하는지, KServe `InferenceService`가 후보 모델 artifact를 가리키는지입니다.

| 항목 | 이번 Lab의 기준 |
| --- | --- |
| 받은 업무 | `risk-classifier@candidate`를 GitOps 방식으로 endpoint 후보에 배포할 수 있는지 확인 |
| 확인 증거 | Argo CD `Application`, Kustomize overlay, MLflow/KServe resource, observability ConfigMap |
| 판단 기준 | manifest inspection, repository credential, Argo CD sync, KServe Ready를 구분 |
| 주의점 | live cluster가 없으면 배포 성공으로 쓰지 않고 `unverified`로 기록 |

## 1. GitOps 배포 단위

Argo CD `Application`은 source repository, target revision, path, destination cluster/namespace, sync policy를 선언합니다. 이 repository의 확인 대상은 다음 파일입니다.

```text
demos/ch03_docker_kubernetes/argocd/application.yaml
```

이 파일의 핵심은 `spec.source.path`입니다.

```text
demos/ch03_docker_kubernetes/gitops/overlays/student
```

이 경로가 Argo CD가 읽는 Kustomize overlay입니다. `gitops/base`에는 공통 Kubernetes resource가 있고, `gitops/overlays/student`에는 수강생 환경에서 바꿀 값이 있습니다.

## 2. 수강생이 수정할 값

MLflow UI ingress 주소는 실습 VM, DNS, tunnel 구성에 따라 다릅니다. 그래서 base를 직접 수정하지 않고 overlay patch를 수정합니다.

```text
demos/ch03_docker_kubernetes/gitops/overlays/student/ingress-host-patch.yaml
```

예시는 다음과 같습니다.

```yaml
- op: replace
  path: /spec/rules/0/host
  value: mlflow.<your-ingress-domain>
```

placeholder가 남아 있으면 live sync 준비가 끝난 것이 아닙니다. 이 상태에서는 manifest inspection까지만 확인했다고 기록합니다.

## 3. GitHub Deploy key로 repository 연결

Argo CD가 GitHub repository를 읽으려면 repository credential이 필요합니다. 이 과정에서는 read-only Deploy key를 사용합니다.

| 위치 | 등록하는 값 | 확인할 기준 |
| --- | --- | --- |
| 로컬 또는 VM | SSH key pair 생성 | private key와 public key가 분리되어 있는가 |
| GitHub repository | Deploy keys에 public key 등록 | `Allow write access`가 꺼져 있는가 |
| Argo CD | repository credential에 private key 등록 | `git@github.com:.../<repo>.git` URL을 읽을 수 있는가 |
| Argo CD `Application` | `spec.source.repoURL` | Deploy key를 등록한 repository SSH URL과 같은가 |

실행 순서는 다음과 같습니다.

```bash
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh check
bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh key

# 출력된 public key를 GitHub repository Settings -> Deploy keys에 등록합니다.
# Allow write access는 체크하지 않습니다.

ARGOCD_REPO_URL=git@github.com:<your-org-or-user>/<your-repo>.git \
  bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh connect

bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh sync
bash demos/ch03_docker_kubernetes/scripts/05_check_kserve_endpoint.sh
```

`connect`는 Argo CD repository credential을 등록하고, `argocd/application.yaml`의 placeholder `repoURL`을 실행 시점에 실제 repository URL로 바꿔 Application을 등록합니다.

## 4. KServe 배포 파일 확인

KServe 배포 파일의 핵심은 `InferenceService`가 후보 모델 artifact와 serving runtime 정보를 담는가입니다.

```text
demos/ch03_docker_kubernetes/gitops/base/inferenceservice.yaml
```

| 확인 항목 | 기대값 | 보고서에 남길 의미 |
| --- | --- | --- |
| resource kind | `InferenceService` | KServe가 처리할 serving 선언 |
| model alias label | `ai-quality/model-alias: candidate` | 현재 운영 모델이 아니라 후보 모델 endpoint임 |
| MLflow URI annotation | `models:/risk-classifier@candidate` | model registry alias와 serving manifest 연결 |
| storage URI | `pvc://ai-quality-models/risk-classifier/candidate-dev` | student overlay가 반영한 model artifact 위치 |
| 응답/로그 필드 | `request_id`, `score`, `prediction`, `latency_ms` 등 | 4장에서 확인할 필드 |

파일 inspection만으로는 Pod readiness, runtime image pull, model loading 성공을 말할 수 없습니다. Argo CD sync와 KServe Ready 확인은 별도 단계입니다.

## 5. 보고서 문장

확인 범위에 따라 문장을 다르게 씁니다.

| 확인한 것 | 쓸 수 있는 문장 | 아직 쓰면 안 되는 문장 |
| --- | --- | --- |
| manifest inspection만 완료 | GitOps 배포 파일은 후보 모델 KServe endpoint를 선언합니다 | 후보 모델 endpoint가 live traffic을 받을 준비가 됐습니다 |
| repository credential 등록 | Argo CD가 Git source를 읽을 credential을 갖습니다 | Application sync가 완료됐습니다 |
| Argo CD sync 완료 | Git의 배포 파일이 cluster에 반영됐습니다 | 모델 응답 품질이 정상입니다 |
| KServe Ready 확인 | KServe resource가 Ready 상태입니다 | `score`, `threshold`, `prediction` 응답 계약이 충족됐습니다 |
| `/predict`와 로그 확인 | 응답과 로그를 배포 판단에 사용할 수 있습니다 | 장기 운영 안정성이 보장됩니다 |

예시:

```text
Argo CD Application은 Git 경로 `demos/ch03_docker_kubernetes/gitops/overlays/student`를 source로 사용하고, KServe `InferenceService`는 `risk-classifier@candidate`와 candidate storage URI를 가리킵니다. 이번 실행에서는 [manifest inspection/live sync/KServe Ready]까지 확인했으며, `/predict` 응답 계약과 운영 관측 증거는 다음 단계에서 확인합니다.
```
