"""Risk API process entry point."""

import uvicorn
from fastapi import FastAPI

from risk_api.bootstrap import build_application
from risk_api.settings import RiskApiSettings


def create_runtime_app() -> FastAPI:
    """Build the public Risk API from its independent runtime settings."""
    return build_application(RiskApiSettings())


def main() -> None:
    """Run the Risk API on its configured public HTTP port."""
    settings = RiskApiSettings()
    uvicorn.run(build_application(settings), host="0.0.0.0", port=settings.port)
