"""Keep the active course journey ordered and bounded."""

from __future__ import annotations

import re
from pathlib import Path

LABS = Path("labs/README.md")
ROOT = Path("README.md")
CHAPTERS = (
    Path("labs/ch01-data-quality/README.md"),
    Path("labs/ch02-model-quality/README.md"),
    Path("labs/ch03-serving/README.md"),
    Path("labs/ch04-observability/README.md"),
    Path("labs/ch05-release-decision/README.md"),
)
STAGE_HEADINGS = (
    "배포된 baseline 관찰",
    "데이터",
    "모델",
    "API",
    "Kubernetes/GitOps",
    "관측",
    "traffic",
    "판단/rollback",
    "회고",
)
STAGE_CHILDREN: dict[str, tuple[str, ...]] = {
    "배포된 baseline 관찰": (
        "baseline API 응답과 선언이 같은 모델 identity를 가리키는지 판단한다",
        "baseline 관찰 결과가 데이터 품질 판단의 출발 근거인지 구분한다",
    ),
    "데이터": (
        "train, valid, sealed test, operational의 역할을 누수 없이 구분한다",
        "PhysioNet raw measurement의 결측, 범위, join을 데이터 품질 근거로 해석한다",
        "GE summary가 데이터 품질 관찰을 재현 가능한 evidence로 닫는지 판단한다",
    ),
    "모델": (
        "Precision, Recall, F1, FP/FN과 PR-AUC를 같은 release 질문으로 해석한다",
        (
            "Candidate A는 HOLD이고 Candidate B는 APPROVE인지 "
            "canonical benchmark로 판정한다"
        ),
        "DVC revision과 MLflow run이 같은 model evidence lineage를 가리키는지 확인한다",
    ),
    "API": (
        "Compose Risk API가 정상 입력과 의도한 422를 같은 계약으로 처리하는지 확인한다",
        (
            "API model metadata와 bundle/deployment 선언이 같은 digest "
            "의미를 갖는지 판단한다"
        ),
    ),
    "Kubernetes/GitOps": (
        (
            "baseline, Candidate B, rollback overlay가 "
            "승인된 identity만 선택하는지 판단한다"
        ),
        "Argo sync, KServe health, rollback 결과를 학습자 판단 범위와 분리한다",
    ),
    "관측": (
        "LIVE/PREPARED 경로와 세 신호의 상관 조건을 실행 전에 정한다",
        "세 신호의 확인 범위와 상태를 traffic 실행 전에 기록 방식으로 고정한다",
    ),
    "traffic": (
        "baseline/current-shift/invalid traffic의 의도와 상태 코드를 인계한다",
        "선택한 대표 요청이 지표, 로그, trace의 동일 사건으로 연결되는지 판정한다",
    ),
    "판단/rollback": (
        "Candidate B 모델 APPROVE와 운영 환경 확인 상태를 한 기록에서 분리한다",
        "rollback trigger와 baseline 복구 완료를 선언할 evidence가 있는지 판단한다",
        "현재 운영 권고가 모델 승인과 분리되는지 기록한다",
    ),
    "회고": (
        "판단 기록에서 판단 변화와 미확인 위험 인계를 복원한다",
    ),
}
GENERIC_CHILD_HEADINGS = (
    "관찰",
    "실행 또는 작은 구현",
    "확인",
    "근거",
    "성찰",
    "LIVE가 없으면",
)
INSTRUCTOR_ONLY = (
    "KServe 설치",
    "GHCR credential",
    "Argo Application 생성",
    "WireGuard",
)


def _h2_headings(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def _section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match is not None, heading
    return match.group(1)


def _h3_headings(section: str) -> list[str]:
    return [
        line[4:].strip()
        for line in section.splitlines()
        if line.startswith("### ")
    ]


def test_setup_course_names_missing_baseline_as_instructor_scope() -> None:
    setup = Path("scripts/setup_course.py").read_text(encoding="utf-8")
    assert "artifacts/models/revisions/v2/deployed/metadata.json" in setup
    assert "instructor/platform scope" in setup
    assert "--data-only" in setup


def test_learner_guide_uses_exact_stage_child_headings() -> None:
    text = LABS.read_text(encoding="utf-8")
    headings = _h2_headings(text)
    assert headings == list(STAGE_HEADINGS)
    assert headings.index("배포된 baseline 관찰") < headings.index("데이터")
    assert tuple(STAGE_CHILDREN) == STAGE_HEADINGS

    observed_children: list[str] = []
    for stage in STAGE_HEADINGS:
        children = tuple(_h3_headings(_section(text, stage)))
        assert children == STAGE_CHILDREN[stage], stage
        observed_children.extend(children)

    assert len(observed_children) == 20
    assert len(set(observed_children)) == 20
    generic = set(GENERIC_CHILD_HEADINGS)
    assert generic.isdisjoint(observed_children)
    all_h3 = tuple(_h3_headings(text))
    assert generic.isdisjoint(all_h3)


def test_root_readme_points_at_baseline_observation_before_data_lab() -> None:
    text = ROOT.read_text(encoding="utf-8")
    observe = text.index("labs/README.md#배포된-baseline-관찰")
    data_lab = text.index("## 4. 데이터 품질 실습")
    assert observe < data_lab
    assert "P0 pending" in text
    assert "http://127.0.0.1:8000" in text
    assert "AIQA_RISK_API_URL" in text


def test_active_docs_do_not_hardcode_host_addresses() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (LABS, ROOT, *CHAPTERS)
    )
    assert "10.99.0." not in combined
    assert "146.56.41.109" not in combined
    assert "ProxyJump mrml-bastion" not in combined


def test_journey_names_instructor_only_external_changes() -> None:
    text = LABS.read_text(encoding="utf-8")
    for token in INSTRUCTOR_ONLY:
        assert token in text
    assert "port-forward" in text
    assert "4GiB" in text
    assert "target_pending" in text


def test_learner_api_start_does_not_build_images() -> None:
    labs = LABS.read_text(encoding="utf-8")
    serving = Path("labs/ch03-serving/README.md").read_text(encoding="utf-8")
    root = ROOT.read_text(encoding="utf-8")
    command = (
        "docker compose -f deploy/compose/simple-mlops/compose.yaml "
        "up -d --no-build risk-api"
    )
    assert command in labs
    assert command in serving
    assert command in root
    assert "up -d --build risk-api" not in labs
    assert "up -d --build risk-api" not in serving


def test_ge_summary_exercise_files_are_in_the_learner_tree() -> None:
    assert Path("labs/exercises/ge_summary/interpret.py").is_file()
    assert Path("labs/exercises/tests/test_ge_summary.py").is_file()
    assert Path("labs/exercises/solutions/ge_summary/interpret.py").is_file()
    ch01 = Path("labs/ch01-data-quality/README.md").read_text(encoding="utf-8")
    assert "labs/exercises/ge_summary/interpret.py" in ch01
    assert "labs/exercises/tests/test_ge_summary.py" in ch01


def test_chapter_guides_link_to_the_journey() -> None:
    labs = LABS.read_text(encoding="utf-8")
    assert "(ch01-data-quality/README.md)" in labs
    assert "(ch03-serving/README.md)" in labs
    assert "(ch04-observability/README.md)" in labs
    assert "(ch05-release-decision/README.md)" in labs
    assert Path("labs/ch01-data-quality/README.md").read_text(
        encoding="utf-8"
    ).count("배포된 baseline 관찰") >= 1
    assert "(ch01-data-quality/README.md#2-남는-시간-실습)" in labs
    assert "(ch02-model-quality/README.md#2-남는-시간-실습)" in labs


def test_chapter_guides_use_numbered_h2_h3() -> None:
    h2 = re.compile(r"^## \d+\. ")
    h3 = re.compile(r"^### \d+-\d+\. ")
    for path in CHAPTERS:
        lines = path.read_text(encoding="utf-8").splitlines()
        h2_headings = [line for line in lines if line.startswith("## ")]
        h3_headings = [line for line in lines if line.startswith("### ")]
        assert h2_headings, path
        assert h3_headings, path
        assert all(h2.match(line) for line in h2_headings), path
        assert all(h3.match(line) for line in h3_headings), path
        assert not any(line.startswith("#### ") for line in lines), path


def test_changed_markdown_links_resolve() -> None:
    paths = (
        LABS,
        ROOT,
        *CHAPTERS,
    )
    link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in link.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resource, _, _anchor = target.partition("#")
            if not resource:
                continue
            resolved = (path.parent / resource).resolve()
            assert resolved.exists(), f"{path}: missing {target}"
