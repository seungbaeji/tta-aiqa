# TTA AIQA Agent Guide

이 파일은 repository 전체에 적용된다. 사용자·시스템 지시와 하위 `AGENTS.md`가 우선한다. 상세 기준은 [README.md](README.md), [V2 TO-BE 계획](docs/v2-to-be-plan.md), [ADR](docs/adr/), [구현 검증 상태](docs/v2-implementation-verification.md)를 따른다.

## ARCHITECTURE IMPLEMENTATION RULES

- **Runtime flow:** `delivery adapter -> application function -> domain / outbound port -> outbound adapter`
- **Static dependency:** `domain <- application/ports <- adapters <- bootstrap/delivery`

- **Domain / DDD:** bounded context는 자기 용어, invariant, decision을 소유한다. identity와 lifecycle이 필요할 때만 entity/aggregate를 만들고, 그 외에는 frozen dataclass, enum, pure function을 사용한다. domain은 표준 라이브러리만 import하며 I/O, framework, Pydantic, repository path를 알지 못한다.
- **Application:** use case는 domain input, 필요한 port, typed result를 받는 named function이다. orchestration만 담당하며 transport, file format, vendor API, framework exception, business policy를 섞지 않는다.
- **Port:** 실제로 교체 가능한 외부 capability나 test boundary에만 `Protocol`을 만든다. port method는 vendor payload가 아니라 domain language를 사용하며, repository는 domain query/consistency 의미가 있을 때만 만든다.
- **Adapter:** inbound adapter는 HTTP/CLI/YAML/JSON을 Pydantic DTO로 검증한 뒤 domain value로 변환한다. outbound adapter는 filesystem, HTTP, sklearn, MLflow, KServe 등 I/O와 기술적 변환을 소유하고 domain policy를 결정하지 않는다.
- **Bootstrap / delivery:** `bootstrap.py`만 concrete adapter와 runtime setting을 조립하고 local closure 또는 `partial`로 use case를 bind한다. delivery는 DTO 변환, bound function 호출, response rendering만 담당한다.
- **Bounded context:** reusable business capability는 package로, process-specific delivery와 composition은 app으로 둔다. business package는 `aiqa-core` 외 다른 business package를 직접 import하지 않으며 app이 명시적으로 결과를 연결한다.
- **Code quality:** public class/function/method에는 역할과 invariant를 설명하는 docstring을 쓴다. role, decision, header, metric, artifact state literal은 owning contract에 한 번만 정의한다.
- **TDD:** domain/application behavior를 failing unit test로 먼저 표현하고 green 뒤 refactor한다. unit은 fake로 public contract와 invariant를, integration은 실제 adapter boundary를 검증한다. private helper의 구현 순서나 호출 횟수는 직접 test하지 않는다.

## HAVE TO

- 교육 문서, 실행 명령, 코드, 테스트, 생성 evidence가 하나의 실제 시나리오와 결과를 가리키게 유지한다.
- active code는 `apps/`, `packages/`, `configs/`, `deploy/`, `labs/`, `scripts/`, `tests/`, `docs/`에 둔다. app은 composition root이고 다른 app을 import하지 않는다.
- versioned YAML/JSON/TOML을 정책의 단일 기준으로 사용한다. runtime setting은 app별 `pydantic-settings`, credential은 app별 secret mount 또는 private env file로 관리한다.
- 데이터와 split은 DVC와 고정 seed로 재현한다. 개발은 `train`/`valid`만 사용하고 sealed `test`와 historical evidence는 새 revision 없이 변경하지 않는다.
- Git, DVC, MLflow, release manifest, immutable runtime digest의 역할을 분리해 provenance를 기록한다. 자세한 기준은 [ADR 0006](docs/adr/0006-layered-artifact-identity-and-release-provenance.md)를 따른다.
- 모든 Python app에 `aiqa-observability`를 적용하고, app이 bounded metric name/label을 소유한다. Alloy와 수강생별 Grafana Cloud만 course monitoring 범위로 둔다.
- TDD로 핵심 public behavior와 invariant를 먼저 검증한다. architecture/policy 변경은 ADR, 외부 환경 pending은 구현 검증 문서에 사실대로 갱신한다.
- 기존 작업 트리를 보존하고, 관련 검증을 마친 뒤에만 사용자가 요청한 scope로 커밋한다.

## HAVE NOT TO

- `tmp/legacy/`를 active runtime dependency로 사용하거나 business bounded context끼리 직접 의존하지 않는다.
- `domain`/application에 FastAPI, pandas, sklearn, MLflow, HTTP, filesystem, YAML parser 같은 외부 기술을 넣지 않는다.
- 의미 없는 base class, service locator, generic use-case/command/result/dependency framework, forwarding-only class를 만들지 않는다.
- feature, threshold, model parameter, release policy를 Python default나 environment variable에 중복 정의하거나 metric/decision을 하드코딩하지 않는다.
- secret, 학생별 credential, generated data/cache/artifact를 Git, image, log, notebook output에 넣지 않는다.
- sealed test 결과를 tuning에 사용하거나 V1/V2 canonical evidence를 덮어쓴다.
- mutable image tag 또는 MLflow alias만으로 runtime deployment를 식별하거나 public Risk API reload를 배포 방식으로 사용한다.
- Grafana, Loki, Tempo, Prometheus backend를 수강생 VM에 배포하거나 request/trace/run ID를 metric label로 사용한다.
- 검증하지 않은 external runtime 결과를 완료라고 쓰거나 task와 무관한 사용자의 변경을 되돌린다.

## VERIFY

```bash
uv lock --check
uv run ruff check apps packages scripts tests
uv run pytest -q
uv run dvc status
```

변경한 경계에 맞는 unit/integration/deployment/notebook 검증을 추가로 실행하고, 실행하지 못한 외부 검증은 이유와 함께 기록한다.
