# Argo CD 릴리스 애플리케이션 만들기

`tta-aiqa.template.yaml`은 직접 적용하는 파일이 아닙니다. 강의 환경이
`main` 같은 가변 브랜치를 따라가지 않도록, 검토를 마친 전체 Git 커밋
40자리와 배포 오버레이를 넣어 실행 파일을 만듭니다.

```bash
REVISION="$(git rev-parse HEAD)"

uv run python scripts/render_argocd_application.py \
  --revision "${REVISION}" \
  --overlay candidate-b
```

기본 출력은 Git이 추적하지 않는
`artifacts/deploy/argocd-tta-aiqa.yaml`입니다. 적용 전에는 다음을
확인합니다.

- `git status --short`가 비어 있는가
- `targetRevision`이 검토한 전체 커밋 40자리와 같은가
- `path`가 이번 변경에서 승인한 오버레이인가
- 과정 릴리스 manifest의 `tta-aiqa` 커밋과 같은가

수강생은 공동 환경에서 이 파일을 적용하지 않습니다. 강사 또는 플랫폼
담당자가 승인 절차에 따라 등록·동기화하고, 실행 중인 모델 정보와 운영
기록을 다시 확인합니다.
