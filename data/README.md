# Data

실습 데이터 위치입니다.

| 경로 | 용도 | Git 포함 여부 |
| --- | --- | --- |
| `human_vital_signs_dataset_2024.csv` | 파생 실습 데이터를 만드는 원본 CSV | 포함 |
| `vital_signs*.csv`, `serving_requests*.csv`, `drift_requests.csv`, `release_regression_cases.csv`, `operational_*.jsonl` | `make prepare-data` 또는 `make labs`가 원본에서 생성하는 파생 데이터 | 제외 |
| `raw/` | 원본 또는 대용량 데이터 | 제외 |
| `derived/` | raw에서 다시 만든 학습용 데이터 | 필요 시 포함 또는 재생성 |

원본 데이터가 있는 환경에서는 다음 명령으로 파생 데이터를 다시 만듭니다.

```bash
uv run python scripts/course.py prepare-data
```

macOS나 Linux에서 `make`를 사용할 수 있다면 `make prepare-data`도 같은 작업을 수행합니다.

원본 데이터가 없는 환경에서도 교재에 제공된 prepared artifact와 JupyterLite용 소형 데이터로 판단 흐름을 따라갈 수 있어야 합니다.
