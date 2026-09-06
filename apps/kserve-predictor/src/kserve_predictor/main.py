"""KServe predictor process entry point."""

import uvicorn
from fastapi import FastAPI

from kserve_predictor.bootstrap import build_application
from kserve_predictor.settings import KServePredictorSettings


def create_runtime_app() -> FastAPI:
    """Build the KServe predictor app from its own runtime settings."""
    return build_application(KServePredictorSettings())


def main() -> None:
    """Run the KServe predictor with the configured HTTP port."""
    settings = KServePredictorSettings()
    uvicorn.run(build_application(settings), host="0.0.0.0", port=settings.port)
