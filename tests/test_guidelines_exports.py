from app.schemas import EMK
from app.services.exporter import export_1c_text, export_html, export_json_package
from app.services.guidelines import StubGuidelinesProvider
from app.services.quality import check_emk_quality


def test_stub_guidelines_are_visible_and_exported():
    emk = EMK.model_validate(
        {
            "complaints": ["Боль при накусывании"],
            "dental": {"tooth_fdi": "36", "odontogram_done": True, "eod_mka": 8},
            "diagnosis": {"code": "K02.1", "title": "Кариес дентина", "confirmed": True},
            "allergy": "отрицает",
            "blood_pressure": "120/80",
        }
    )
    evidence = StubGuidelinesProvider().search(emk, "зуб 36 кариес")
    findings = check_emk_quality(emk)

    assert evidence
    assert evidence[0].is_stub is True
    assert "KR 1021_1" in export_json_package(emk, findings, evidence)
    assert "КР Минздрава" in export_html(emk, findings, evidence)
    assert "Live-write" in export_1c_text(emk, findings, evidence)
