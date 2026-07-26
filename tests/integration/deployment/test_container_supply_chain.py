"""Keep classroom container base images immutable by default."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BASE = (
    "python:3.11-slim@sha256:"
    "db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93"
)
DOCKERFILES = (
    ROOT / "apps/model-trainer/Dockerfile",
    ROOT / "apps/traffic-generator/Dockerfile",
    ROOT / "apps/kserve-predictor/Dockerfile",
    ROOT / "apps/risk-api/Dockerfile",
)


def test_course_images_pin_the_same_multi_arch_python_base() -> None:
    for dockerfile in DOCKERFILES:
        first_line = dockerfile.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == f"FROM {EXPECTED_BASE}", dockerfile


def test_setup_uses_a_versioned_reviewable_uv_installer() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "https://astral.sh/uv/0.11.12/install.sh" in readme
    assert "https://astral.sh/uv/0.11.12/install.ps1" in readme
    assert "install.sh | sh" not in readme
    assert "install.ps1 | iex" not in readme
