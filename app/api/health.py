from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import processor
from app.core.config import get_settings
from app.core.gpu import GPUUnavailableError, assert_gpu_ready

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health() -> dict[str, object]:
    settings = get_settings()
    try:
        gpu = assert_gpu_ready(required=settings.gpu_required)
        gpu_payload: dict[str, object] = {
            "ok": gpu.available,
            "name": gpu.name,
            "total_mb": gpu.total_mb,
            "free_mb": gpu.free_mb,
            "driver": gpu.driver,
        }
    except GPUUnavailableError as exc:
        gpu_payload = {"ok": False, "reason": str(exc)}

    llm_ok = await processor.extractor.llm.health()
    return {
        "ok": gpu_payload["ok"] and (llm_ok or not settings.require_llm),
        "gpu": gpu_payload,
        "llm": {
            "ok": llm_ok,
            "url": settings.llama_server_url,
            "model": settings.llama_model,
            "required": settings.require_llm,
        },
        "asr": {
            "model": settings.asr_model,
            "language": settings.asr_language,
            "compute_type": settings.asr_compute_type,
            "device": settings.asr_device,
        },
    }
