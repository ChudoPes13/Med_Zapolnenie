from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, delete, select

from app.db.models import AuditEvent, EvidenceRef, Finding, TranscriptSegment, Visit
from app.schemas import EMK, EvidenceOut, FindingOut, VisitOut, VisitState
from app.services.clinical import ClinicalExtractor
from app.services.emk import apply_emk_patch, initial_emk, normalize_emk
from app.services.guidelines import GuidelinesProvider, StubGuidelinesProvider
from app.services.quality import check_emk_quality


def build_final_summary(transcript: list[str], emk: EMK) -> str:
    parts = []
    if emk.complaints:
        parts.append(f"Жалобы: {'; '.join(emk.complaints)}")
    if emk.age_years:
        parts.append(f"Возраст: {emk.age_years} лет")
    if emk.clinical_focus == "lower_limb":
        lower = emk.lower_limb
        parts.append(
            "Нижние конечности: "
            f"сторона {lower.side or '-'}, локализация {lower.location or '-'}, "
            f"пульс стопы {lower.dorsalis_pedis_pulse or lower.posterior_tibial_pulse or '-'}, "
            f"кожа {lower.skin_color or '-'} / {lower.skin_temperature or '-'}"
        )
    if emk.clinical_focus == "dental":
        dental = emk.dental
        parts.append(
            "Стоматология: "
            f"зуб {dental.tooth_fdi or '-'}, перкуссия {dental.percussion or '-'}, "
            f"ЭОД {dental.eod_mka or '-'}"
        )
    if emk.blood_pressure:
        parts.append(f"АД: {emk.blood_pressure}")
    if emk.allergy:
        parts.append(f"Аллергия: {emk.allergy}")
    if emk.diagnosis.code:
        parts.append(f"Диагноз: {emk.diagnosis.code} {emk.diagnosis.title or ''}".strip())
    if parts:
        return ". ".join(parts) + "."
    return " ".join(transcript).strip()


def visit_to_out(visit: Visit) -> VisitOut:
    return VisitOut(
        id=visit.id,
        created_at=visit.created_at,
        updated_at=visit.updated_at,
        status=visit.status,
        doctor_confirmed=visit.doctor_confirmed,
        patient_label=visit.patient_label,
        emk=normalize_emk(visit.emk),
    )


def create_visit(session: Session, patient_label: str | None = None) -> Visit:
    visit = Visit(patient_label=patient_label, emk=initial_emk())
    session.add(visit)
    session.add(
        AuditEvent(
            visit_id=visit.id,
            action="visit.created",
            payload={"patient_label": patient_label},
        )
    )
    session.commit()
    session.refresh(visit)
    return visit


def get_visit_or_raise(session: Session, visit_id: str) -> Visit:
    visit = session.get(Visit, visit_id)
    if visit is None:
        raise KeyError(visit_id)
    return visit


def current_findings(session: Session, visit_id: str) -> list[FindingOut]:
    rows = session.exec(select(Finding).where(Finding.visit_id == visit_id)).all()
    return [
        FindingOut(
            code=row.code,
            severity=row.severity,  # type: ignore[arg-type]
            title=row.title,
            message=row.message,
            section=row.section,
            status=row.status,  # type: ignore[arg-type]
        )
        for row in rows
    ]


def current_evidence(session: Session, visit_id: str) -> list[EvidenceOut]:
    rows = session.exec(select(EvidenceRef).where(EvidenceRef.visit_id == visit_id)).all()
    return [
        EvidenceOut(
            kr_id=row.kr_id,
            title=row.title,
            section=row.section,
            fragment=row.fragment,
            url=row.url,
            score=row.score,
            is_stub=row.is_stub,
        )
        for row in rows
    ]


def visit_state(session: Session, visit_id: str) -> VisitState:
    visit = get_visit_or_raise(session, visit_id)
    transcript = session.exec(
        select(TranscriptSegment)
        .where(TranscriptSegment.visit_id == visit_id)
        .order_by(TranscriptSegment.created_at)
    ).all()
    return VisitState(
        visit=visit_to_out(visit),
        transcript=[row.text for row in transcript],
        findings=current_findings(session, visit_id),
        evidence=current_evidence(session, visit_id),
    )


def _replace_findings(session: Session, visit_id: str, findings: list[FindingOut]) -> None:
    session.exec(delete(Finding).where(Finding.visit_id == visit_id))
    for item in findings:
        session.add(
            Finding(
                visit_id=visit_id,
                code=item.code,
                severity=item.severity,
                title=item.title,
                message=item.message,
                section=item.section,
                status=item.status,
            )
        )


def _replace_evidence(session: Session, visit_id: str, evidence: list[EvidenceOut]) -> None:
    session.exec(delete(EvidenceRef).where(EvidenceRef.visit_id == visit_id))
    for item in evidence:
        session.add(
            EvidenceRef(
                visit_id=visit_id,
                kr_id=item.kr_id,
                title=item.title,
                section=item.section,
                fragment=item.fragment,
                url=item.url,
                score=item.score,
                is_stub=item.is_stub,
            )
        )


class VisitProcessor:
    def __init__(
        self,
        extractor: ClinicalExtractor | None = None,
        guidelines: GuidelinesProvider | None = None,
    ) -> None:
        self.extractor = extractor or ClinicalExtractor()
        self.guidelines = guidelines or StubGuidelinesProvider()

    async def process_text(
        self,
        session: Session,
        visit_id: str,
        text: str,
        source: str,
    ) -> VisitState:
        visit = get_visit_or_raise(session, visit_id)
        session.add(TranscriptSegment(visit_id=visit_id, text=text.strip(), source=source))

        patch = await self.extractor.extract_patch(text, visit.emk or initial_emk())
        visit.emk = apply_emk_patch(visit.emk or initial_emk(), patch)
        visit.updated_at = datetime.now(UTC)
        visit.doctor_confirmed = False
        visit.status = "draft"

        emk = EMK.model_validate(visit.emk)
        findings = check_emk_quality(emk, final=False)
        evidence = self.guidelines.search(emk, text)
        _replace_findings(session, visit_id, findings)
        _replace_evidence(session, visit_id, evidence)

        session.add(
            AuditEvent(
                visit_id=visit_id,
                action="transcript.processed",
                payload={"source": source, "text": text, "patch": patch},
            )
        )
        session.add(visit)
        session.commit()
        return visit_state(session, visit_id)

    def finalize_visit(self, session: Session, visit_id: str) -> VisitState:
        visit = get_visit_or_raise(session, visit_id)
        transcript_rows = session.exec(
            select(TranscriptSegment)
            .where(TranscriptSegment.visit_id == visit_id)
            .order_by(TranscriptSegment.created_at)
        ).all()
        transcript = [row.text for row in transcript_rows]
        emk = EMK.model_validate(visit.emk or initial_emk())
        final_summary = build_final_summary(transcript, emk)
        visit.emk = {**emk.model_dump(), "final_summary": final_summary}
        visit.status = "ready_for_confirmation"
        visit.doctor_confirmed = False
        visit.updated_at = datetime.now(UTC)

        emk = EMK.model_validate(visit.emk)
        findings = check_emk_quality(emk, final=True)
        evidence = self.guidelines.search(emk, " ".join(transcript))
        _replace_findings(session, visit_id, findings)
        _replace_evidence(session, visit_id, evidence)
        session.add(
            AuditEvent(
                visit_id=visit_id,
                action="recording.finalized",
                payload={"summary": final_summary, "segments": len(transcript)},
            )
        )
        session.add(visit)
        session.commit()
        return visit_state(session, visit_id)
