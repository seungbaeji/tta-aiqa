"""Keep classroom container images on a pinned builder-release pattern."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BASE = (
    "python:3.11-slim@sha256:"
    "db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93"
)
DOCKERFILES = (
    ROOT / "apps/model_trainer/Dockerfile",
    ROOT / "apps/traffic_generator/Dockerfile",
    ROOT / "apps/kserve_predictor/Dockerfile",
    ROOT / "apps/risk_api/Dockerfile",
)
BUILDER_FROM = f"FROM {EXPECTED_BASE} AS builder"
RELEASE_FROM = f"FROM {EXPECTED_BASE} AS release"


def _from_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("FROM ")]


def _builder_stage(text: str) -> str:
    return text.split("AS release", 1)[0]


def _release_stage(text: str) -> str:
    return text.split("AS release", 1)[1]


def test_course_images_pin_the_same_multi_arch_python_base() -> None:
    for dockerfile in DOCKERFILES:
        assert _from_lines(dockerfile.read_text(encoding="utf-8")) == [
            BUILDER_FROM,
            RELEASE_FROM,
        ], dockerfile


def test_course_images_use_builder_release_stages() -> None:
    for dockerfile in DOCKERFILES:
        text = dockerfile.read_text(encoding="utf-8")
        builder = _builder_stage(text)
        release = _release_stage(text)

        assert "uv sync --frozen --no-dev --package " in builder
        assert "pip install --no-cache-dir uv==0.11.12" in builder
        assert "COPY --from=builder /workspace/.venv /workspace/.venv" in release
        assert "COPY --from=builder /workspace/apps /workspace/apps" in release
        assert (
            "COPY --from=builder /workspace/packages /workspace/packages" in release
        )
        assert "USER 65532:65532" in release
        assert "uv sync" not in release
        assert "pip install" not in release


def test_setup_uses_a_versioned_reviewable_uv_installer() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "https://astral.sh/uv/0.11.12/install.sh" in readme
    assert "https://astral.sh/uv/0.11.12/install.ps1" in readme
    assert "install.sh | sh" not in readme
    assert "install.ps1 | iex" not in readme
