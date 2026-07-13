from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import data_service
from .schemas import (
    AssetsResponse,
    ConfigResponse,
    DatesResponse,
    HealthResponse,
    MacroHistoryResponse,
    MacroOverviewResponse,
    MacroReadinessResponse,
    PlaybackResponse,
    ReadinessResponse,
    SnapshotResponse,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
REQUEST_LOGGER = logging.getLogger("cross_asset_dashboard.requests")


def _configure_request_logger() -> None:
    if REQUEST_LOGGER.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    REQUEST_LOGGER.addHandler(handler)
    REQUEST_LOGGER.setLevel(logging.INFO)
    REQUEST_LOGGER.propagate = False


def create_app(config_path: str | Path | None = None) -> FastAPI:
    resolved_config_path = data_service.resolve_config_path(config_path)
    _configure_request_logger()
    app = FastAPI(title="Local Asset Terminal", version="1.0.0")
    app.state.config_path = resolved_config_path
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            REQUEST_LOGGER.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    },
                    separators=(",", ":"),
                )
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get(
        "/api/ready",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse}},
    )
    def ready(response: Response) -> ReadinessResponse:
        readiness = ReadinessResponse(
            **data_service.get_readiness(resolved_config_path)
        )
        if readiness.status != "ready":
            response.status_code = 503
        return readiness

    @app.get("/api/config", response_model=ConfigResponse)
    def config() -> ConfigResponse:
        return data_service.load_config_response(resolved_config_path)

    @app.get("/api/dates", response_model=DatesResponse)
    def dates() -> DatesResponse:
        return DatesResponse(dates=data_service.get_dates(resolved_config_path))

    @app.get("/api/assets", response_model=AssetsResponse)
    def assets() -> AssetsResponse:
        return AssetsResponse(assets=data_service.get_assets(resolved_config_path))

    @app.get("/api/snapshot", response_model=SnapshotResponse)
    def snapshot(date: str = Query(...)) -> SnapshotResponse:
        if date not in data_service.get_dates(resolved_config_path):
            raise HTTPException(status_code=404, detail=f"No snapshot for date {date}")
        return SnapshotResponse(
            date=date,
            items=data_service.get_snapshot(date, resolved_config_path),
        )

    @app.get("/api/playback", response_model=PlaybackResponse)
    def playback(start: str | None = None, end: str | None = None) -> PlaybackResponse:
        dates, frames = data_service.get_playback(
            start,
            end,
            resolved_config_path,
        )
        return PlaybackResponse(dates=dates, frames=frames)

    @app.get(
        "/api/macro/ready",
        response_model=MacroReadinessResponse,
        responses={503: {"model": MacroReadinessResponse}},
    )
    def macro_ready(response: Response) -> MacroReadinessResponse:
        readiness = MacroReadinessResponse(**data_service.get_macro_readiness(resolved_config_path))
        if readiness.status == "not_ready":
            response.status_code = 503
        return readiness

    @app.get("/api/macro/overview", response_model=MacroOverviewResponse)
    def macro_overview(as_of: str | None = None) -> MacroOverviewResponse:
        return MacroOverviewResponse(**data_service.get_macro_overview(as_of, resolved_config_path))

    @app.get("/api/macro/history", response_model=MacroHistoryResponse)
    def macro_history(
        series_id: str = Query(...),
        start: str | None = None,
        end: str | None = None,
    ) -> MacroHistoryResponse:
        history = data_service.get_macro_history(series_id, start, end, resolved_config_path)
        if history is None:
            raise HTTPException(status_code=404, detail=f"Unknown macro series {series_id}")
        return MacroHistoryResponse(**history)

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
