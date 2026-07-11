"""Prepare derived datasets used by the course labs."""

from __future__ import annotations

from ai_quality.data_quality.application.prepare_course_datasets import (
    prepare_datasets,
)


def main() -> None:
    """Generate derived datasets and print output paths."""
    for path in prepare_datasets():
        print(path)


if __name__ == "__main__":
    main()
