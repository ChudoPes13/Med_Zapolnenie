from app.schemas import EMK
from app.services.clinical import deterministic_dental_patch
from app.services.emk import apply_emk_patch, initial_emk
from app.services.quality import check_emk_quality


def test_dental_acceptance_scenario_turns_core_findings_green():
    emk = initial_emk()
    emk = apply_emk_patch(
        emk,
        deterministic_dental_patch("Болит зуб, нижняя челюсть, боль при накусывании."),
    )
    first = {item.code: item for item in check_emk_quality(EMK.model_validate(emk))}
    assert first["tooth_fdi.required"].status == "open"
    assert first["diagnosis.confirm"].status == "open"

    emk = apply_emk_patch(
        emk,
        deterministic_dental_patch(
            "Зуб 36, перкуссия отрицательная, ЭОД 8 мкА, аллергии нет, "
            "АД 120/80, подтверждаю K02.1 кариес."
        ),
    )
    second = {item.code: item for item in check_emk_quality(EMK.model_validate(emk))}
    assert second["tooth_fdi.required"].status == "resolved"
    assert second["odontogram.required"].status == "resolved"
    assert second["percussion.required"].status == "resolved"
    assert second["eod.required"].status == "resolved"
    assert second["allergy.required"].status == "resolved"
    assert second["bp.required"].status == "resolved"
    assert second["diagnosis.confirm"].status == "resolved"
