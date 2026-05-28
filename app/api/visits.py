from __future__ import annotations

import base64
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.api.deps import processor
from app.core.config import get_settings
from app.db.models import AuditEvent, DoctorConfirmation, ExportRecord
from app.db.session import get_session
from app.schemas import (
    ConfirmationIn,
    ExportResponse,
    TranscriptIn,
    VisitCreate,
    VisitOut,
    VisitState,
)
from app.services.exporter import (
    export_1c_text,
    export_docx_bytes,
    export_html,
    export_json_package,
)
from app.services.visit_processor import (
    create_visit,
    current_evidence,
    current_findings,
    get_visit_or_raise,
    visit_state,
    visit_to_out,
)

router = APIRouter(prefix="/api/visits", tags=["visits"])


@router.post("", response_model=VisitOut)
def create(payload: VisitCreate, session: Session = Depends(get_session)) -> VisitOut:
    return visit_to_out(create_visit(session, payload.patient_label))


@router.get("/{visit_id}", response_model=VisitState)
def get_state(visit_id: str, session: Session = Depends(get_session)) -> VisitState:
    try:
        return visit_state(session, visit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="visit not found") from None


@router.post("/{visit_id}/transcript", response_model=VisitState)
async def add_transcript(
    visit_id: str,
    payload: TranscriptIn,
    session: Session = Depends(get_session),
) -> VisitState:
    try:
        return await processor.process_text(session, visit_id, payload.text, payload.source)
    except KeyError:
        raise HTTPException(status_code=404, detail="visit not found") from None


@router.post("/{visit_id}/confirm", response_model=VisitOut)
def confirm(
    visit_id: str,
    payload: ConfirmationIn,
    session: Session = Depends(get_session),
) -> VisitOut:
    try:
        visit = get_visit_or_raise(session, visit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="visit not found") from None

    visit.doctor_confirmed = True
    visit.status = "confirmed"
    session.add(
        DoctorConfirmation(visit_id=visit_id, scope=payload.scope, payload=payload.payload)
    )
    session.add(
        AuditEvent(
            visit_id=visit_id,
            action="doctor.confirmed",
            payload={"scope": payload.scope, "payload": payload.payload},
        )
    )
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit_to_out(visit)


def _export_payload(session: Session, visit_id: str) -> tuple[str, str, str]:
    visit = get_visit_or_raise(session, visit_id)
    if not visit.doctor_confirmed:
        raise HTTPException(status_code=409, detail="doctor confirmation required before export")
    emk = visit_to_out(visit).emk
    findings = current_findings(session, visit_id)
    evidence = current_evidence(session, visit_id)
    return (
        export_json_package(emk, findings, evidence),
        export_html(emk, findings, evidence),
        export_1c_text(emk, findings, evidence),
    )


@router.get("/{visit_id}/exports/docx")
def export_docx(visit_id: str, session: Session = Depends(get_session)) -> Response:
    try:
        visit = get_visit_or_raise(session, visit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="visit not found") from None
    if not visit.doctor_confirmed:
        raise HTTPException(status_code=409, detail="doctor confirmation required before export")

    emk = visit_to_out(visit).emk
    body = export_docx_bytes(
        emk,
        current_findings(session, visit_id),
        current_evidence(session, visit_id),
    )
    settings = get_settings()
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(settings.export_dir) / f"{visit_id}.docx"
    out_path.write_bytes(body)
    session.add(
        ExportRecord(
            visit_id=visit_id,
            export_type="docx",
            path=str(out_path),
            payload={"filename": out_path.name},
        )
    )
    session.add(AuditEvent(visit_id=visit_id, action="export.created", payload={"type": "docx"}))
    session.commit()
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{out_path.name}"'},
    )


@router.get("/{visit_id}/exports/docx-base64")
def export_docx_base64(visit_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    response = export_docx(visit_id, session)
    return {
        "filename": f"{visit_id}.docx",
        "content_base64": base64.b64encode(response.body).decode(),
    }


@router.get("/{visit_id}/exports/{export_type}", response_model=ExportResponse)
def export_text(
    visit_id: str,
    export_type: str,
    session: Session = Depends(get_session),
) -> ExportResponse:
    try:
        json_body, html_body, one_c_body = _export_payload(session, visit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="visit not found") from None

    mapping = {
        "json": ("visit.json", json_body, "application/json"),
        "html": ("visit.html", html_body, "text/html; charset=utf-8"),
        "1c": ("visit-1c.txt", one_c_body, "text/plain; charset=utf-8"),
    }
    if export_type not in mapping:
        raise HTTPException(status_code=400, detail="export_type must be json, html or 1c")
    filename, content, media_type = mapping[export_type]
    session.add(
        ExportRecord(
            visit_id=visit_id,
            export_type=export_type,
            payload={"filename": filename, "media_type": media_type},
        )
    )
    session.add(
        AuditEvent(visit_id=visit_id, action="export.created", payload={"type": export_type})
    )
    session.commit()
    return ExportResponse(
        export_type=export_type,
        filename=filename,
        content=content,
        media_type=media_type,
    )
