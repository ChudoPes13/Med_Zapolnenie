from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.visits import router as visits_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from app.core.gpu import assert_gpu_ready
from app.db.session import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(visits_router)
app.include_router(ws_router)


@app.on_event("startup")
def startup() -> None:
    assert_gpu_ready(required=settings.gpu_required)
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running"}
