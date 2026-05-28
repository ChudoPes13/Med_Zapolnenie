from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas import EMK


def initial_emk() -> dict[str, Any]:
    return EMK().model_dump()


def normalize_emk(payload: dict[str, Any] | None) -> EMK:
    return EMK.model_validate(payload or initial_emk())


def merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    result = list(existing)
    lowered = {item.casefold() for item in result}
    for item in incoming:
        clean = item.strip()
        if clean and clean.casefold() not in lowered:
            result.append(clean)
            lowered.add(clean.casefold())
    return result


def apply_emk_patch(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    emk = normalize_emk(current).model_dump()
    patch = deepcopy(patch)

    for key in ("complaints", "anamnesis", "objective", "recommendations"):
        if key in patch and isinstance(patch[key], list):
            emk[key] = merge_unique(emk.get(key, []), patch[key])

    if allergy := patch.get("allergy"):
        emk["allergy"] = allergy
    if blood_pressure := patch.get("blood_pressure"):
        emk["blood_pressure"] = blood_pressure

    dental_patch = patch.get("dental") or {}
    if isinstance(dental_patch, dict):
        emk["dental"].update(
            {key: value for key, value in dental_patch.items() if value is not None}
        )

    diagnosis_patch = patch.get("diagnosis") or {}
    if isinstance(diagnosis_patch, dict):
        emk["diagnosis"].update(
            {key: value for key, value in diagnosis_patch.items() if value is not None}
        )

    if prescriptions := patch.get("prescriptions"):
        known = {
            (
                item.get("name"),
                item.get("dose"),
                item.get("frequency"),
                item.get("duration"),
            )
            for item in emk["prescriptions"]
        }
        for item in prescriptions:
            marker = (
                item.get("name"),
                item.get("dose"),
                item.get("frequency"),
                item.get("duration"),
            )
            if item.get("name") and marker not in known:
                emk["prescriptions"].append(item)
                known.add(marker)

    return normalize_emk(emk).model_dump()
