from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .data_service import get_assets, get_dates, get_playback, get_snapshot, load_config_response
from .schemas import AssetsResponse, ConfigResponse, DatesResponse, HealthResponse, PlaybackResponse, SnapshotResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

app = FastAPI(title="Local Asset Terminal", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_local_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    return load_config_response()


@app.get("/api/dates", response_model=DatesResponse)
def dates() -> DatesResponse:
    return DatesResponse(dates=get_dates())


@app.get("/api/assets", response_model=AssetsResponse)
def assets() -> AssetsResponse:
    return AssetsResponse(assets=get_assets())


@app.get("/api/snapshot", response_model=SnapshotResponse)
def snapshot(date: str = Query(...)) -> SnapshotResponse:
    if date not in get_dates():
        raise HTTPException(status_code=404, detail=f"No snapshot for date {date}")
    return SnapshotResponse(date=date, items=get_snapshot(date))


@app.get("/api/playback", response_model=PlaybackResponse)
def playback(start: str | None = None, end: str | None = None) -> PlaybackResponse:
    dates, frames = get_playback(start, end)
    return PlaybackResponse(dates=dates, frames=frames)


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
