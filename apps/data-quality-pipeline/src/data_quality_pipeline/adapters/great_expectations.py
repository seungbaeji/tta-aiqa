"""Great Expectations checkpoint adapter for pandas dataframes."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations.checkpoint import Checkpoint
from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.core.validation_definition import ValidationDefinition
from great_expectations.expectations.expectation import Expectation


def run_checkpoint(
    dataframe: pd.DataFrame,
    *,
    name: str,
    expectations: list[Expectation],
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Run one named dataframe checkpoint and return JSON-safe GE evidence."""
    if project_root is None:
        context = gx.get_context(mode="ephemeral")
    else:
        generated_context = project_root / "gx"
        if generated_context.exists():
            shutil.rmtree(generated_context)
        project_root.mkdir(parents=True, exist_ok=True)
        context = gx.get_context(mode="file", project_root_dir=project_root)

    datasource = context.data_sources.add_pandas(name=f"{name}-datasource")
    asset = datasource.add_dataframe_asset(name=f"{name}-asset")
    batch = asset.add_batch_definition_whole_dataframe(name=f"{name}-whole")
    suite = ExpectationSuite(name=f"{name}-suite")
    for expectation in expectations:
        suite.add_expectation(expectation)
    suite = context.suites.add(suite)
    validation = context.validation_definitions.add(
        ValidationDefinition(name=f"{name}-validation", data=batch, suite=suite)
    )
    checkpoint = context.checkpoints.add(
        Checkpoint(name=f"{name}-checkpoint", validation_definitions=[validation])
    )
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": dataframe})
    validation_result = next(iter(checkpoint_result.run_results.values()))
    result = validation_result.to_json_dict()
    result["checkpoint_success"] = checkpoint_result.success
    result["data_docs"] = context.build_data_docs() if project_root else {}
    return result
