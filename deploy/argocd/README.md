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

uv run python scripts/render_argocd_application.py \
  --revision "${REVISION}" \
  --overlay baseline \
  --application-name tta-aiqa-student-201 \
  --destination-namespace tta-aiqa \
  --destination-server https://10.99.0.201:6443
```

로컬 Argo와 같은 클러스터에만 둘 때:

```bash
uv run python scripts/render_argocd_application.py \
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

수강생은 공동 환경에서 이 파일을 적용하지 않습니다. 강사 또는 플랫폼
담당자가 승인 절차에 따라 등록·동기화하고, 실행 중인 모델 정보와 운영
기록을 다시 확인합니다.

모델 번들을 학생 VM hostPath `/mnt/course-models`에 둘 때는 디렉터리를
`tta` 소유로 만듭니다. root로만 `mkdir` 하면 publish가 실패합니다.

```bash
sudo mkdir -p /mnt/course-models
sudo chown tta:tta /mnt/course-models
# then as tta, no sudo:
uv run python scripts/publish_model.py baseline --revision v2 --target-root /mnt/course-models
uv run python scripts/publish_model.py candidate-b --revision v2 --target-root /mnt/course-models
```
