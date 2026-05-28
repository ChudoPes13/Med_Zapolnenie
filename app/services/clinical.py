from __future__ import annotations

import re
from typing import Any

from app.services.llm import LLMUnavailableError, LlamaServerClient


TOOTH_RE = re.compile(r"\b([1-4][1-8]|[5-8][1-5])\b")
EOD_RE = re.compile(r"(?:эод|eod)\D{0,12}(\d{1,3})", re.IGNORECASE)
BP_RE = re.compile(r"\b(1\d{2}|[8-9]\d)\s*/\s*(\d{2,3})\b")


def deterministic_dental_patch(text: str) -> dict[str, Any]:
    low = text.casefold()
    patch: dict[str, Any] = {}

    complaints: list[str] = []
    objective: list[str] = []
    anamnesis: list[str] = []
    recommendations: list[str] = []

    if "болит" in low or "боль" in low:
        complaints.append(text.strip())
    if "накусыв" in low:
        complaints.append("Боль при накусывании")
        patch["diagnosis"] = {
            "code": "K02.1",
            "title": "Кариес дентина",
            "confidence": 0.62,
            "confirmed": False,
        }
        recommendations.append("Уточнить локализацию зуба и выполнить дифференциальные пробы.")
    if "нижн" in low and "челюст" in low:
        complaints.append("Боль в области нижней челюсти")

    dental: dict[str, Any] = {}
    tooth_match = TOOTH_RE.search(text)
    if tooth_match:
        dental["tooth_fdi"] = tooth_match.group(1)
        dental["odontogram_done"] = True
        objective.append(f"Указан зуб {tooth_match.group(1)} по FDI")

    if "перкус" in low:
        if "отриц" in low or "безбол" in low:
            dental["percussion"] = "отрицательная"
        elif "полож" in low or "болез" in low:
            dental["percussion"] = "положительная"
        else:
            dental["percussion"] = "уточняется"

    if "термо" in low or "холод" in low or "тепл" in low:
        dental["thermal_test"] = "зафиксирована в диалоге"

    if eod_match := EOD_RE.search(text):
        dental["eod_mka"] = int(eod_match.group(1))

    if "аллерг" in low:
        if "нет" in low or "отрица" in low:
            patch["allergy"] = "отрицает"
        else:
            anamnesis.append("Требуется уточнить аллергоанамнез")

    if bp_match := BP_RE.search(text):
        patch["blood_pressure"] = f"{bp_match.group(1)}/{bp_match.group(2)}"

    if "подтверж" in low and ("k02.1" in low or "кариес" in low):
        patch["diagnosis"] = {
            "code": "K02.1",
            "title": "Кариес дентина",
            "confidence": 0.9,
            "confirmed": True,
        }

    if complaints:
        patch["complaints"] = complaints
    if objective:
        patch["objective"] = objective
    if anamnesis:
        patch["anamnesis"] = anamnesis
    if recommendations:
        patch["recommendations"] = recommendations
    if dental:
        patch["dental"] = dental

    return patch


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            result[key] = [*result[key], *value]
        elif value not in (None, "", [], {}):
            result[key] = value
    return result


class ClinicalExtractor:
    def __init__(self, llm: LlamaServerClient | None = None) -> None:
        self.llm = llm or LlamaServerClient()

    async def extract_patch(self, text: str, current_emk: dict[str, Any]) -> dict[str, Any]:
        rule_patch = deterministic_dental_patch(text)
        try:
            llm_patch = await self.llm.extract_json(text, current_emk)
        except LLMUnavailableError:
            return rule_patch
        return _deep_merge(llm_patch, rule_patch)
