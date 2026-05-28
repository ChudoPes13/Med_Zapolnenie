from fastapi.testclient import TestClient

from app.main import app


def test_visit_lifecycle_requires_confirmation_before_export():
    with TestClient(app) as client:
        created = client.post("/api/visits", json={"patient_label": "test"}).json()
        visit_id = created["id"]

        state = client.post(
            f"/api/visits/{visit_id}/transcript",
            json={"text": "Болит зуб, нижняя челюсть, боль при накусывании.", "source": "test"},
        ).json()
        assert "Боль при накусывании" in state["visit"]["emk"]["complaints"]

        blocked = client.get(f"/api/visits/{visit_id}/exports/json")
        assert blocked.status_code == 409

        client.post(
            f"/api/visits/{visit_id}/transcript",
            json={
                "text": (
                    "Зуб 36, перкуссия отрицательная, ЭОД 8 мкА, аллергии нет, "
                    "АД 120/80, подтверждаю K02.1 кариес."
                ),
                "source": "test",
            },
        )
        confirmed = client.post(
            f"/api/visits/{visit_id}/confirm",
            json={"scope": "visit", "payload": {"test": True}},
        )
        assert confirmed.status_code == 200
        exported = client.get(f"/api/visits/{visit_id}/exports/json")
        assert exported.status_code == 200
        assert exported.json()["export_type"] == "json"
