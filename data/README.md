# Data

Git에는 원본 CSV인 `human_vital_signs_dataset_2024.csv`만 포함합니다.

Simple MLOps demo가 사용하는 파생 데이터는 루트에서 다시 생성합니다.

```bash
uv run python scripts/prepare_data.py
```

생성 파일은 `.gitignore`에 의해 제외됩니다.

```text
vital_signs_train.csv
vital_signs_test.csv
serving_requests.csv
serving_requests_current.csv
serving_requests_invalid.csv
operational_current_events.jsonl
```
