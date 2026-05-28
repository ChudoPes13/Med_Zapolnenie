from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import EMK, EvidenceOut


class GuidelinesProvider(Protocol):
    def search(self, emk: EMK, query: str) -> list[EvidenceOut]:
        ...


@dataclass
class StubGuidelinesProvider:
    kr_id: str = "KR 1021_1"
    title: str = "Клинические рекомендации: кариес зубов, стоматология"

    def search(self, emk: EMK, query: str) -> list[EvidenceOut]:
        evidence: list[EvidenceOut] = []
        if emk.clinical_focus == "lower_limb":
            return [
                EvidenceOut(
                    kr_id="KR-STUB-LOWER-LIMB",
                    title="Заглушка: требуется подключение реальной базы КР/БМ25",
                    section="Первичная оценка жалоб на нижние конечности",
                    fragment=(
                        "Для жалоб на нижние конечности система проверяет локализацию, "
                        "сосудистый и неврологический статус. Это не официальный источник."
                    ),
                    url="stub://kr/lower-limb/triage",
                    score=0.5,
                    is_stub=True,
                )
            ]

        tooth = emk.dental.tooth_fdi

        if tooth or "зуб" in query.casefold() or "кариес" in query.casefold():
            evidence.append(
                EvidenceOut(
                    kr_id=self.kr_id,
                    title=self.title,
                    section="Диагностика",
                    fragment=(
                        "Для постановки диагноза в стоматологической карте фиксируются зуб, "
                        "жалобы, данные осмотра и результаты дополнительных проб."
                    ),
                    url="stub://kr/1021_1/diagnostics",
                    score=0.91,
                    is_stub=True,
                )
            )

        if emk.diagnosis.code == "K02.1" or "накусыв" in query.casefold():
            evidence.append(
                EvidenceOut(
                    kr_id=self.kr_id,
                    title=self.title,
                    section="Лечение",
                    fragment=(
                        "План лечения выбирается после подтверждения локализации пораженного "
                        "зуба, витальности пульпы и дифференциальной диагностики."
                    ),
                    url="stub://kr/1021_1/treatment",
                    score=0.87,
                    is_stub=True,
                )
            )

        return evidence
