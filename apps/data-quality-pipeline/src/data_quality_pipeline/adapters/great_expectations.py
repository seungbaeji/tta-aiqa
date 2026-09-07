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
    """Run one named dataframe checkpoint and return JSON-safe GE evidence.

    GX 실행 순서는 Data Context → pandas Batch → Expectation Suite →
    Validation Definition → Checkpoint → run 입니다. 규칙 값은 이 함수가
    정하지 않고, 호출 측이 넘긴 expectations 목록을 그대로 적용합니다.
    """
    # project_root가 없으면 메모리만 쓰는 ephemeral context입니다(단위 테스트).
    # 있으면 file context로 Data Docs를 artifact 디렉터리에 만듭니다.
    if project_root is None:
        context = gx.get_context(mode="ephemeral")
    else:
        generated_context = project_root / "gx"
        if generated_context.exists():
            shutil.rmtree(generated_context)
        project_root.mkdir(parents=True, exist_ok=True)
        context = gx.get_context(mode="file", project_root_dir=project_root)

    # 디스크 CSV가 아니라 이미 만든 DataFrame 한 장을 Batch로 등록합니다.
    datasource = context.data_sources.add_pandas(name=f"{name}-datasource")
    asset = datasource.add_dataframe_asset(name=f"{name}-asset")
    batch = asset.add_batch_definition_whole_dataframe(name=f"{name}-whole")
    suite = ExpectationSuite(name=f"{name}-suite")
    for expectation in expectations:
        suite.add_expectation(expectation)
    suite = context.suites.add(suite)
    # Validation Definition은 “어떤 데이터에 어떤 Suite를 적용할지”의 고정 연결입니다.
    validation = context.validation_definitions.add(
        ValidationDefinition(name=f"{name}-validation", data=batch, suite=suite)
    )
    # Checkpoint는 그 연결을 실제로 한 번 실행하는 경계입니다.
    checkpoint = context.checkpoints.add(
        Checkpoint(name=f"{name}-checkpoint", validation_definitions=[validation])
    )
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": dataframe})
    validation_result = next(iter(checkpoint_result.run_results.values()))
    result = validation_result.to_json_dict()
    result["checkpoint_success"] = checkpoint_result.success
    # Data Docs는 사람이 읽는 HTML입니다. Git 근거로 쓰지 않고 artifact에만 둡니다.
    result["data_docs"] = context.build_data_docs() if project_root else {}
    return result
