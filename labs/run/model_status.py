"""Show the frozen V2 model status for the course journey."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", choices=("v1", "v2"), default="v2")
    args = parser.parse_args()
    path = (
        ROOT
        / (
            "docs/evidence/model-v2/canonical-benchmark.json"
            if args.revision == "v2"
            else "docs/evidence/model-v1/canonical-benchmark.json"
        )
    )
    if not path.exists():
        print(json.dumps({"revision": args.revision, "status": "NOT_EVALUATED"}, indent=2))
        return 0
    document = json.loads(path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "revision": args.revision,
                "status": document["status"],
                "deployment_allowed": document["deployment_allowed"],
                "sealed_test": document["sealed_test"]["status"],
                "decisions": {
                    item["profile"]: item["decision"] for item in document["decisions"]
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
