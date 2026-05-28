from fastapi.testclient import TestClient

from app.main import app


def test_general_abdominal_complaint_is_filled_and_filler_is_ignored():
    with TestClient(app) as client:
        visit_id = client.post("/api/visits", json={"patient_label": "dialogue"}).json()["id"]
        first = client.post(
            f"/api/visits/{visit_id}/transcript",
            json={
                "text": "пациента зовут мастеров александр владимирович жалуются на боли в животе",
                "source": "test",
            },
        ).json()
        assert "Боли в животе" in first["visit"]["emk"]["complaints"]
        assert first["visit"]["emk"]["dental"]["tooth_fdi"] is None

        second = client.post(
            f"/api/visits/{visit_id}/transcript",
            json={"text": "Ну ладно. Привет! Как меня слышно? медленно.", "source": "test"},
        ).json()
        assert second["visit"]["emk"]["complaints"] == first["visit"]["emk"]["complaints"]

        finalized = client.post(f"/api/visits/{visit_id}/finalize").json()
        codes = {finding["code"]: finding for finding in finalized["findings"]}
        assert codes["complaints.required"]["status"] == "resolved"
        assert finalized["visit"]["emk"]["final_summary"]
