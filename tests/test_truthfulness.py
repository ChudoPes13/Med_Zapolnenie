import pytest

from app.schemas import EMK
from app.services.clinical import ClinicalExtractor, deterministic_clinical_patch
from app.services.emk import apply_emk_patch, initial_emk
from app.services.quality import check_emk_quality


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Пациента зовут Мастеров Александр Владимирович, жалуются на боли в животе.",
            {
                "focus": "general",
                "tooth": None,
                "complaint": "Боли в животе",
            },
        ),
        (
            "Ну ладно. Привет! Как меня слышно? медленно.",
            {
                "focus": "general",
                "tooth": None,
                "complaint_count": 0,
            },
        ),
        (
            "У пациента боль в нижних конечностях. Ему 17 лет.",
            {
                "focus": "lower_limb",
                "age": 17,
                "tooth": None,
                "location": "нижние конечности",
            },
        ),
        (
            "Правая голень отечна, стопа холодная, пульс на тыльной артерии стопы не определяется.",
            {
                "focus": "lower_limb",
                "side": "правая",
                "location": "голень",
                "edema": "есть",
                "temperature": "холодная",
                "pulse": "не определяется",
                "tooth": None,
            },
        ),
        (
            "Есть онемение стопы и слабость движений, после ходьбы 100 метров боль усиливается.",
            {
                "focus": "lower_limb",
                "sensitivity": "нарушена",
                "movement": "ограничено",
                "tooth": None,
            },
        ),
        (
            "Пациенту 36 лет, болит левая нога.",
            {
                "focus": "lower_limb",
                "age": 36,
                "side": "левая",
                "tooth": None,
            },
        ),
        (
            "Размер обуви 36, жалобы на боль в стопе.",
            {
                "focus": "lower_limb",
                "location": "стопа",
                "tooth": None,
            },
        ),
        (
            "Болит зуб 36, боль при накусывании, ЭОД 8 мкА.",
            {
                "focus": "dental",
                "tooth": "36",
                "eod": 8,
                "diagnosis": "K02.1",
            },
        ),
    ],
)
def test_synthetic_dialogue_truthfulness(text, expected):
    emk = apply_emk_patch(initial_emk(), deterministic_clinical_patch(text))
    parsed = EMK.model_validate(emk)

    assert parsed.clinical_focus == expected["focus"]
    assert parsed.dental.tooth_fdi == expected.get("tooth")
    if "age" in expected:
        assert parsed.age_years == expected["age"]
    if "side" in expected:
        assert parsed.lower_limb.side == expected["side"]
    if "location" in expected:
        assert parsed.lower_limb.location == expected["location"]
    if "edema" in expected:
        assert parsed.lower_limb.edema == expected["edema"]
    if "temperature" in expected:
        assert parsed.lower_limb.skin_temperature == expected["temperature"]
    if "pulse" in expected:
        assert parsed.lower_limb.dorsalis_pedis_pulse == expected["pulse"]
    if "sensitivity" in expected:
        assert parsed.lower_limb.sensitivity == expected["sensitivity"]
    if "movement" in expected:
        assert parsed.lower_limb.movement == expected["movement"]
    if "eod" in expected:
        assert parsed.dental.eod_mka == expected["eod"]
    if "diagnosis" in expected:
        assert parsed.diagnosis.code == expected["diagnosis"]
    if "complaint" in expected:
        assert expected["complaint"] in parsed.complaints
    if "complaint_count" in expected:
        assert len(parsed.complaints) == expected["complaint_count"]


def test_lower_limb_quality_is_profile_specific_and_has_no_dental_required_fields():
    emk = apply_emk_patch(
        initial_emk(),
        deterministic_clinical_patch("У пациента боль в нижних конечностях. Ему 17 лет."),
    )
    findings = check_emk_quality(EMK.model_validate(emk), final=False)
    codes = {finding.code for finding in findings}

    assert "lower_limb.location.required" in codes
    assert "lower_limb.pulses.required" in codes
    assert "tooth_fdi.required" not in codes
    assert "odontogram.required" not in codes


class HallucinatingLLM:
    async def extract_json(self, _text, _current_emk):
        return {
            "clinical_focus": "dental",
            "dental": {"tooth_fdi": "17", "odontogram_done": True},
            "diagnosis": {"code": "K02.1", "title": "Кариес дентина", "confirmed": False},
        }


@pytest.mark.asyncio
async def test_llm_hallucinated_dental_patch_is_removed_without_dental_context():
    extractor = ClinicalExtractor(llm=HallucinatingLLM())
    patch = await extractor.extract_patch(
        "У пациента боль в нижних конечностях. Ему 17 лет.",
        initial_emk(),
    )

    assert patch["clinical_focus"] == "lower_limb"
    assert patch["age_years"] == 17
    assert "dental" not in patch
    assert "diagnosis" not in patch


class NonObjectLLM:
    async def extract_json(self, _text, _current_emk):
        return ["complaints", "боль", "invalid-patch"]


@pytest.mark.asyncio
async def test_llm_non_object_json_is_ignored_without_breaking_rules():
    extractor = ClinicalExtractor(llm=NonObjectLLM())
    patch = await extractor.extract_patch(
        "жалуется на боли в передней челюсти.",
        initial_emk(),
    )

    assert patch["complaints"] == ["Боли в передней челюсти"]


class LowercaseComplaintLLM:
    async def extract_json(self, _text, _current_emk):
        return {"complaints": ["боли в животе"]}


@pytest.mark.asyncio
async def test_rule_normalized_complaint_takes_precedence_over_llm_variant():
    extractor = ClinicalExtractor(llm=LowercaseComplaintLLM())
    patch = await extractor.extract_patch(
        "пациент жалуется на боли в животе",
        initial_emk(),
    )

    assert patch["complaints"][0] == "Боли в животе"
