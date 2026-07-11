"""Send fake production traffic to the prediction API.

실제 운영에서는 사용자의 요청이 계속 들어옵니다. 이 스크립트는 CSV 샘플을 조금씩
변형해서 /predict로 보내고, 응답을 JSONL로 저장하는 간단한 traffic generator입니다.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
from aiqa_core.contracts import FEATURE_COLUMNS


def parse_args() -> argparse.Namespace:
    # Docker Compose에서는 기본값을 그대로 쓰고, 로컬 테스트 때만 인자를 바꿉니다.
    parser = argparse.ArgumentParser(description="Send fake production traffic.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--data-path", default="/app/data/serving_requests.csv")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--retry-sleep", type=float, default=5.0)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-path",
        default="/app/events/fake_traffic_responses.jsonl",
    )
    return parser.parse_args()


def jitter(row: dict[str, float], rng: random.Random) -> dict[str, float]:
    """Create a slightly changed copy of one source row.

    같은 CSV 행만 계속 보내면 운영 데이터처럼 보이지 않으므로 작은 noise를 추가합니다.
    """

    return {
        "heart_rate": round(float(row["heart_rate"]) + rng.uniform(-8, 8), 2),
        "respiratory_rate": round(
            float(row["respiratory_rate"]) + rng.uniform(-2, 2),
            2,
        ),
        "body_temperature": round(
            float(row["body_temperature"]) + rng.uniform(-0.3, 0.3),
            2,
        ),
        "oxygen_saturation": round(
            min(100.0, max(50.0, float(row["oxygen_saturation"]) + rng.uniform(-2, 1))),
            2,
        ),
        "systolic_blood_pressure": round(
            float(row["systolic_blood_pressure"]) + rng.uniform(-12, 12),
            2,
        ),
        "diastolic_blood_pressure": round(
            float(row["diastolic_blood_pressure"]) + rng.uniform(-8, 8),
            2,
        ),
    }


def append_response(path: str, payload: dict[str, object]) -> None:
    """Save API responses as JSONL so students can inspect them later."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    # serving_requests.csv에서 API 입력 feature만 사용합니다.
    dataframe = pd.read_csv(args.data_path).loc[:, list(FEATURE_COLUMNS)]
    sent = 0

    while True:
        # 매 loop마다 순서를 섞어 같은 패턴의 요청만 반복되는 것을 피합니다.
        shuffled = dataframe.sample(frac=1, random_state=rng.randint(1, 10**9))
        for _, source_row in shuffled.iterrows():
            request_id = f"fake-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{sent}"
            payload = jitter(source_row.to_dict(), rng)
            payload["request_id"] = request_id
            try:
                # 운영 client처럼 HTTP로 FastAPI endpoint를 호출합니다.
                response = requests.post(
                    f"{args.api_url.rstrip('/')}/predict",
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as error:
                if not args.loop:
                    raise
                print(f"request failed, retrying: {error}", flush=True)
                time.sleep(args.retry_sleep)
                continue

            body = response.json()
            append_response(args.output_path, body)
            sent += 1

            # 로그에는 핵심 결과만 작게 출력해서
            # docker compose logs에서 보기 쉽게 합니다.
            print(
                json.dumps(
                    {
                        "request_id": body["request_id"],
                        "predicted_label": body["predicted_label"],
                        "risk_probability": round(body["risk_probability"], 4),
                    },
                    ensure_ascii=False,
                )
            )
            if sent >= args.count and not args.loop:
                return
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
