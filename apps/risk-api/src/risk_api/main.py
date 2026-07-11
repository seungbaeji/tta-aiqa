"""Risk API process entry point."""

import uvicorn

from risk_api.bootstrap import build_application
from risk_api.settings import RiskApiSettings


def create_runtime_app():
    return build_application(RiskApiSettings())


def main() -> None:
    uvicorn.run(create_runtime_app(), host="0.0.0.0", port=8000)
