"""Render the course Argo CD Application with an immutable Git revision."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "deploy/argocd/tta-aiqa.template.yaml"
DEFAULT_OUTPUT = ROOT / "artifacts/deploy/argocd-tta-aiqa.yaml"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_OVERLAYS = {"baseline", "baseline-observed", "candidate-b", "rollback"}


def render(revision: str, overlay: str) -> str:
    """Bind a reviewed commit and known overlay to the Application template."""

    if not COMMIT_PATTERN.fullmatch(revision):
        raise ValueError("revision must be a full 40-character lowercase Git commit")
    if overlay not in ALLOWED_OVERLAYS:
        allowed = ", ".join(sorted(ALLOWED_OVERLAYS))
        raise ValueError(f"overlay must be one of: {allowed}")

    source = TEMPLATE.read_text(encoding="utf-8")
    rendered = source.replace("__TTA_AIQA_REVISION__", revision)
    rendered = rendered.replace("__TTA_AIQA_OVERLAY__", overlay)
    if "__TTA_AIQA_" in rendered:
        raise ValueError("not all Argo CD template placeholders were replaced")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--overlay", choices=sorted(ALLOWED_OVERLAYS), required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(args.revision, args.overlay), encoding="utf-8")
    print(f"rendered immutable Argo CD application: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
