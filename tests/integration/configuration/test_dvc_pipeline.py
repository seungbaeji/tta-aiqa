"""DVC pipeline contracts for reproducible course data preparation."""

import subprocess
from pathlib import Path

import yaml


def test_stage_outputs_do_not_overlap() -> None:
    """Require each generated path to have exactly one owning DVC output."""
    document = yaml.safe_load(Path("dvc.yaml").read_text(encoding="utf-8"))

    for stage_name, stage in document["stages"].items():
        outputs = [Path(output) for output in stage.get("outs", ())]
        for index, output in enumerate(outputs):
            others = outputs[:index] + outputs[index + 1 :]
            assert not any(
                output.is_relative_to(other) or other.is_relative_to(output)
                for other in others
            ), f"{stage_name} has overlapping outputs: {outputs}"


def test_directory_outputs_do_not_contain_git_tracked_files() -> None:
    """Keep generated DVC directories under DVC ownership, not mixed SCM ownership."""
    document = yaml.safe_load(Path("dvc.yaml").read_text(encoding="utf-8"))
    tracked_files = {
        Path(line)
        for line in subprocess.run(
            ("git", "ls-files"),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    }

    for stage_name, stage in document["stages"].items():
        for output in (Path(item) for item in stage.get("outs", ())):
            if output.suffix:
                continue
            conflicts = [
                path
                for path in tracked_files
                if path.exists() and path.is_relative_to(output)
            ]
            assert not conflicts, (
                f"{stage_name} output {output} contains Git files: {conflicts}"
            )
