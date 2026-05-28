from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.deps import asr
from app.api.health import router as health_router
from app.api.visits import router as visits_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from app.core.gpu import assert_gpu_ready
from app.db.session import init_db
from app.services.llm import LlamaServerClient

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    assert_gpu_ready(required=settings.gpu_required)
    if settings.require_llm and not await LlamaServerClient().health():
        raise RuntimeError(
            "MEDJARVIS_REQUIRE_LLM=1, but llama-server is unavailable at "
            f"{settings.llama_server_url}. Start scripts\\start_llama.ps1 first."
        )
    if settings.asr_preload:
        await run_in_threadpool(asr.load)
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
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

@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running"}
