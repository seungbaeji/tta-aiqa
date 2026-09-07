"""Run repository raw and processed GE checkpoints with default workspace paths.

수강생은 이 스크립트만 실행합니다. 실제 Great Expectations 호출은
`data_quality_pipeline.main validate`가 adapter에서 수행합니다.
결과는 artifacts/data-quality/great-expectations/ 에 남고, 게시 차단 조건이 아닙니다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    # 과정 기본 경로를 CLI로 묶습니다. 규칙 숫자는 Python default가 아니라 YAML입니다.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "data_quality_pipeline.main",
            "validate",
            # 원본 기록 위치, 48시간 관측 창, 기대 건수
            "--source-contract",
            str(ROOT / "configs/contracts/physionet-record.yaml"),
            # 133개 특성으로 접는 집계 규칙
            "--aggregation-config",
            str(ROOT / "configs/data/aggregation.yaml"),
            "--split-config",
            str(ROOT / "params.yaml"),
            # 가공 특성 표. 원본 4,000개 txt를 여기서 다시 붙이지 않습니다.
            "--patient-features",
            str(ROOT / "data/features.csv"),
            "--split-manifest",
            str(ROOT / "data/splits-v1/split-manifest.csv"),
            "--split-dataset-dir",
            str(ROOT / "data/splits-v1"),
            "--source-evidence",
            str(ROOT / "artifacts/data-quality/source-integrity.json"),
            # 행 수, 2880분 상한, target 허용값. Expectation 숫자가 여기서 나옵니다.
            "--quality-rules",
            str(ROOT / "configs/data/quality-rules.yaml"),
            # 체크포인트 JSON, Data Docs. Git에 커밋하지 않는 생성물입니다.
            "--validation-artifact-dir",
            str(ROOT / "artifacts/data-quality/great-expectations"),
        ],
        check=True,
        cwd=ROOT,
    )


if __name__ == "__main__":
    main()
