"""Dataset reader port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class DatasetReader(Protocol):
    """Read a dataset into a dataframe-like structure."""

    def read(self, dataset_path: Path) -> pd.DataFrame:
        """Read a dataset from disk."""
        raise NotImplementedError
