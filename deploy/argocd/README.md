# Argo CD 릴리스 애플리케이션 만들기

`tta-aiqa.template.yaml`은 직접 적용하는 파일이 아닙니다. 강의 환경이
`main` 같은 가변 브랜치를 따라가지 않도록, 검토를 마친 전체 Git 커밋
40자리와 배포 오버레이, **명시적 Application 이름과 destination**을 넣어
실행 파일을 만듭니다.

공유 Argo에서 학생 클러스터로 보낼 때는 `kubernetes.default.svc`를 쓰지
않습니다. in-cluster destination은 `--in-cluster`로만 허용합니다.
`syncPolicy`는 `CreateNamespace=true`만 넣으며 automated prune/selfHeal은
렌더하지 않습니다.

```bash
REVISION="$(git rev-parse HEAD)"

uv run python scripts/platform/render_argocd_application.py \
  --revision "${REVISION}" \
  --overlay baseline \
  --application-name tta-aiqa-student-201 \
  --destination-namespace tta-aiqa \
  --destination-server https://10.99.0.201:6443
```

로컬 Argo와 같은 클러스터에만 둘 때:

```bash
uv run python scripts/platform/render_argocd_application.py \
  --revision "${REVISION}" \
  --overlay baseline \
  --application-name tta-aiqa \
  --destination-namespace tta-aiqa \
  --in-cluster
```

기본 출력은 Git이 추적하지 않는
`artifacts/deploy/argocd-tta-aiqa.yaml`입니다. 적용 전에는 다음을
확인합니다.

- `git status --short`가 비어 있는가
- `metadata.name`이 이번 학생/환경 Application 이름인가
- `spec.destination.server` 또는 `name`이 승인한 클러스터인가.
  학생 VM은 `kubernetes.default.svc`가 아니어야 한다
- `targetRevision`이 검토한 전체 커밋 40자리와 같은가
- `path`가 이번 변경에서 승인한 오버레이인가
- automated/prune/selfHeal이 없는가
- 과정 릴리스 manifest의 `tta-aiqa` 커밋과 같은가

수강생은 이 YAML을 `kubectl apply`로 적용하지 않습니다. 공유 Argo
(`https://gitops.lab.mrml.dev`)에 강사가 알려 준 `tta` 계정으로 접속해 같은
필드(저장소, 커밋 40자리, overlay 경로, Application 이름, 학생 클러스터
destination)로 git 저장소를 연결하고 Application을 만들어 동기화합니다.
KServe 설치와 GHCR pull secret은 플랫폼 담당자가 승인 절차에 따라 준비합니다.
이미 만든 Application을 `deploy/k8s/candidate-b`로 바꾸고 대상 `/v1/model`을
확인하는 것도 수강생 범위입니다.

모델 번들을 학생 VM hostPath `/mnt/course-models`에 둘 때는 디렉터리를
`tta` 소유로 만듭니다. root로만 `mkdir` 하면 publish가 실패합니다. 기준
모델 게시는 플랫폼이 준비합니다.

```bash
sudo mkdir -p /mnt/course-models
sudo chown tta:tta /mnt/course-models
# then as tta, no sudo:
uv run python scripts/platform/publish_model.py baseline --revision v2 --target-root /mnt/course-models
```

## 이미 등록된 Application을 Candidate B로 바꾸기

클러스터를 바꾸기 전에 `TARGET_CONTEXT`가 승인된 컨텍스트와 같은지
확인합니다. 값이 비어 있거나 현재 컨텍스트와 다르면 동기화 스크립트가
거절합니다. 학생 VM destination은 `kubernetes.default.svc`가 아니어야
하며, automated prune/selfHeal을 켜지 않습니다.

```bash
if [ -z "${TARGET_CONTEXT:-}" ]; then
  echo "TARGET_CONTEXT is required; refusing to change a cluster." >&2
  exit 1
fi
CURRENT_CONTEXT="$(kubectl config current-context)" || {
  echo "Unable to read the current Kubernetes context; refusing to continue." >&2
  exit 1
}
if [ "$CURRENT_CONTEXT" != "$TARGET_CONTEXT" ]; then
  echo "Context mismatch: expected $TARGET_CONTEXT, got $CURRENT_CONTEXT" >&2
  exit 1
fi

uv run python scripts/platform/publish_model.py candidate-b --revision v2 --target-root /mnt/course-models
uv run python scripts/platform/sync_student_release.py \
  --application-name "${AIQA_ARGOCD_APPLICATION_NAME:?already-registered Application name}"
curl "${AIQA_RISK_API_URL:?Risk API base URL is required}/v1/model"
```

`/v1/model`의 `version`은 `candidate-b-c712a8e52344`와 같아야 합니다. 대상
URL이 없으면 `operational_deployment_scope=target_pending`으로 두고
identity를 만들지 않습니다. 실패하면 `result=BLOCKED`와 사유를 기록합니다.
이 확인은 공식 평가나 sealed test를 다시 실행한 것이 아닙니다.
