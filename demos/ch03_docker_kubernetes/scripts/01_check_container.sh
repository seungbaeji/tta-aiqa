#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

curl -fsS "http://${HOST}:${PORT}/health"
echo

curl -fsS \
  -X POST "http://${HOST}:${PORT}/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "docker-smoke-001",
    "heart_rate": 80,
    "respiratory_rate": 15,
    "body_temperature": 36.8,
    "oxygen_saturation": 98,
    "systolic_blood_pressure": 120,
    "diastolic_blood_pressure": 80
  }'
echo
