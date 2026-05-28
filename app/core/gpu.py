from __future__ import annotations

import subprocess
from dataclasses import dataclass


class GPUUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GPUStatus:
    available: bool
    name: str | None = None
    total_mb: int | None = None
    free_mb: int | None = None
    driver: str | None = None
    reason: str | None = None


def inspect_nvidia_smi() -> GPUStatus:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:  # pragma: no cover - depends on workstation
        return GPUStatus(available=False, reason=str(exc))

    first = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    parts = [part.strip() for part in first.split(",")]
    if len(parts) < 4:
        return GPUStatus(available=False, reason="nvidia-smi returned no GPU rows")

    return GPUStatus(
        available=True,
        name=parts[0],
        total_mb=int(parts[1]),
        free_mb=int(parts[2]),
        driver=parts[3],
    )


def assert_torch_cuda() -> None:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - import depends on env
        raise GPUUnavailableError(f"torch is not importable: {exc}") from exc

    if not torch.cuda.is_available():
        raise GPUUnavailableError("torch.cuda.is_available() is false")


def assert_gpu_ready(required: bool = True) -> GPUStatus:
    status = inspect_nvidia_smi()
    if required and not status.available:
        raise GPUUnavailableError(status.reason or "NVIDIA GPU is not available")
    if required:
        assert_torch_cuda()
    return status
