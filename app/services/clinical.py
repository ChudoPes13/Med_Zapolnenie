from __future__ import annotations

import re
from typing import Any

from app.core.config import get_settings
from app.services.llm import LlamaServerClient, LLMUnavailableError

TOOTH_RE = re.compile(r"\b([1-4][1-8]|[5-8][1-5])\b")
AGE_RE = re.compile(r"\b(\d{1,3})\s*(?:год|года|лет)\b", re.IGNORECASE)
EOD_RE = re.compile(r"(?:эод|eod)\D{0,12}(\d{1,3})", re.IGNORECASE)
BP_RE = re.compile(r"\b(1\d{2}|[8-9]\d)\s*/\s*(\d{2,3})\b")
COMPLAINT_AFTER_NA_RE = re.compile(
    r"(?:жал\w*|жалоб\w*)\s+на\s+([^.;\n]+)",
    re.IGNORECASE,
)
PAIN_RE = re.compile(r"\b(?:боль|боли|болит|болят|болезненн\w*)\b", re.IGNORECASE)
FILLER_WORDS = (
    "слышно",
    "привет",
    "спасибо",
    "ладно",
    "медленно",
    "проверка",
)
DENTAL_WORDS = (
    "зуб",
    "зуба",
    "зубе",
    "зубы",
    "кариес",
    "пульпит",
    "периодонтит",
    "челюст",
    "одонт",
    "эод",
    "fdi",
)
LOWER_LIMB_WORDS = (
    "нижн",
    "конечност",
    "нога",
    "ноге",
    "ноги",
    "бедр",
    "голен",
    "стоп",
    "икр",
    "колен",
    "лодыж",
    "пальц",
    "хромот",
)


def has_dental_context(text: str) -> bool:
    low = text.casefold()
    return any(word in low for word in DENTAL_WORDS)


def has_lower_limb_context(text: str) -> bool:
    low = text.casefold()
    return any(word in low for word in LOWER_LIMB_WORDS)


def _extract_age(text: str) -> int | None:
    if match := AGE_RE.search(text):
        age = int(match.group(1))
        if 0 < age < 130:
            return age
    return None


def _extract_tooth(text: str) -> str | None:
    if not has_dental_context(text):
        return None
    low = text.casefold()
    if "лет" in low or "год" in low or "возраст" in low:
        return None
    if match := re.search(r"(?:зуб|fdi)\D{0,8}([1-4][1-8]|[5-8][1-5])\b", low):
        return match.group(1)
    return None


def _is_filler(text: str) -> bool:
    low = text.casefold().strip()
    if len(low) <= 3:
        return True
    return any(word in low for word in FILLER_WORDS) and not PAIN_RE.search(low)


def _clean_complaint(value: str) -> str:
    clean = value.strip(" .,:;!?-")
    if not clean:
        return ""
    return clean[0].upper() + clean[1:]


def deterministic_general_patch(text: str) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if age := _extract_age(text):
        patch["age_years"] = age
    if _is_filler(text):
        return patch

    complaints: list[str] = []
    if match := COMPLAINT_AFTER_NA_RE.search(text):
        complaint = _clean_complaint(match.group(1))
        if complaint:
            complaints.append(complaint)
    elif PAIN_RE.search(text):
        complaints.append(_clean_complaint(text))

    if complaints:
        patch["complaints"] = complaints
    return patch


def deterministic_dental_patch(text: str) -> dict[str, Any]:
    low = text.casefold()
    patch: dict[str, Any] = {}

    complaints: list[str] = []
    objective: list[str] = []
    anamnesis: list[str] = []
    recommendations: list[str] = []

    if "болит" in low or "боль" in low:
        complaints.append(text.strip())

    if not has_dental_context(text):
        if complaints:
            patch["complaints"] = complaints
        return patch

    patch["clinical_focus"] = "dental"

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
    tooth = _extract_tooth(text)
    if tooth:
        dental["tooth_fdi"] = tooth
        dental["odontogram_done"] = True
        objective.append(f"Указан зуб {tooth} по FDI")

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


def deterministic_lower_limb_patch(text: str) -> dict[str, Any]:
    low = text.casefold()
    patch: dict[str, Any] = {}
    complaints: list[str] = []
    objective: list[str] = []
    anamnesis: list[str] = []
    recommendations: list[str] = []
    lower_limb: dict[str, Any] = {}

    if age := _extract_age(text):
        patch["age_years"] = age
        anamnesis.append(f"Возраст пациента: {age} лет")

    if not has_lower_limb_context(text):
        if anamnesis:
            patch["anamnesis"] = anamnesis
        return patch

    patch["clinical_focus"] = "lower_limb"

    if "боль" in low or "болит" in low:
        complaints.append(text.strip())
        lower_limb["pain"] = "есть"
    if "нижн" in low and "конеч" in low:
        complaints.append("Боль или дискомфорт в нижних конечностях")
        lower_limb["location"] = "нижние конечности"
    if "прав" in low:
        lower_limb["side"] = "правая"
    elif "лев" in low:
        lower_limb["side"] = "левая"
    elif "обе" in low or "двух" in low or "двусторон" in low:
        lower_limb["side"] = "обе"

    for location_word, label in (
        ("бедр", "бедро"),
        ("голен", "голень"),
        ("стоп", "стопа"),
        ("колен", "колено"),
        ("лодыж", "лодыжка"),
        ("икр", "икроножная область"),
    ):
        if location_word in low:
            lower_limb["location"] = label
            break

    if "отек" in low or "отёк" in low or "отеч" in low:
        lower_limb["edema"] = "есть"
        objective.append("Отек нижней конечности зафиксирован в диалоге")
    if "циан" in low or "синюш" in low:
        lower_limb["skin_color"] = "цианоз/синюшность"
    elif "блед" in low:
        lower_limb["skin_color"] = "бледность"
    elif "покрас" in low or "гиперем" in low:
        lower_limb["skin_color"] = "гиперемия"

    if "холод" in low:
        lower_limb["skin_temperature"] = "холодная"
    elif "тепл" in low:
        lower_limb["skin_temperature"] = "теплая"

    if "тыльн" in low and "стоп" in low and "пульс" in low:
        lower_limb["dorsalis_pedis_pulse"] = "не определяется" if "не " in low else "определяется"
    if ("задн" in low and "большеберц" in low and "пульс" in low) or "posterior tibial" in low:
        lower_limb["posterior_tibial_pulse"] = "не определяется" if "не " in low else "определяется"

    if "онемен" in low or "чувств" in low:
        lower_limb["sensitivity"] = (
            "нарушена" if ("онемен" in low or "снижен" in low) else "сохранена"
        )
    if "движ" in low or "слабост" in low:
        lower_limb["movement"] = (
            "ограничено" if ("слабост" in low or "огранич" in low) else "сохранено"
        )
    if "травм" in low or "удар" in low or "паден" in low:
        lower_limb["trauma"] = "есть"
    if "хромот" in low or "ходьб" in low or "метр" in low:
        lower_limb["walking_limit"] = text.strip()
    if "кров" in low and "взять" in low:
        recommendations.append(
            "Уточнить показания к лабораторным анализам и назначить обследование."
        )

    if complaints:
        patch["complaints"] = complaints
    if objective:
        patch["objective"] = objective
    if anamnesis:
        patch["anamnesis"] = anamnesis
    if recommendations:
        patch["recommendations"] = recommendations
    if lower_limb:
        patch["lower_limb"] = lower_limb
    return patch


def deterministic_clinical_patch(text: str) -> dict[str, Any]:
    patch = deterministic_general_patch(text)
    lower_limb_patch = deterministic_lower_limb_patch(text)
    patch = _deep_merge(patch, lower_limb_patch)
    dental_patch = deterministic_dental_patch(text)
    return _deep_merge(patch, dental_patch)


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


def sanitize_patch_for_context(
    patch: dict[str, Any],
    text: str,
    current_emk: dict[str, Any],
) -> dict[str, Any]:
    sanitized = dict(patch)
    current_focus = str(current_emk.get("clinical_focus") or "general")
    dental_allowed = has_dental_context(text) or current_focus == "dental"
    lower_limb_allowed = has_lower_limb_context(text) or current_focus == "lower_limb"

    if not dental_allowed:
        sanitized.pop("dental", None)
        diagnosis = sanitized.get("diagnosis")
        if isinstance(diagnosis, dict) and str(diagnosis.get("code", "")).upper().startswith("K02"):
            sanitized.pop("diagnosis", None)
        if sanitized.get("clinical_focus") == "dental":
            sanitized.pop("clinical_focus", None)

    if not lower_limb_allowed and sanitized.get("clinical_focus") == "lower_limb":
        sanitized.pop("clinical_focus", None)

    if age := _extract_age(text):
        sanitized["age_years"] = age
    return sanitized


class ClinicalExtractor:
    def __init__(self, llm: LlamaServerClient | None = None) -> None:
        provided_llm = llm is not None
        self.llm = llm or LlamaServerClient()
        self.llm_enabled = provided_llm or get_settings().require_llm

    async def extract_patch(self, text: str, current_emk: dict[str, Any]) -> dict[str, Any]:
        rule_patch = deterministic_clinical_patch(text)
        if not self.llm_enabled:
            return rule_patch
        try:
            llm_patch = await self.llm.extract_json(text, current_emk)
        except LLMUnavailableError:
            return rule_patch
        if not isinstance(llm_patch, dict):
            return rule_patch
        llm_patch = sanitize_patch_for_context(llm_patch, text, current_emk)
        merged = _deep_merge(llm_patch, rule_patch)
        return _prefer_rule_lists(merged, rule_patch)


def _prefer_rule_lists(merged: dict[str, Any], rule_patch: dict[str, Any]) -> dict[str, Any]:
    for key in ("complaints", "anamnesis", "objective", "recommendations"):
        rule_items = rule_patch.get(key)
        merged_items = merged.get(key)
        if not isinstance(rule_items, list) or not isinstance(merged_items, list):
            continue
        seen = {str(item).casefold() for item in rule_items}
        tail = [item for item in merged_items if str(item).casefold() not in seen]
        merged[key] = [*rule_items, *tail]
    return merged
