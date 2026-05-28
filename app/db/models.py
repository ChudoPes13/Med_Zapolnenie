from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Visit(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    status: str = Field(default="draft", index=True)
    doctor_confirmed: bool = Field(default=False)
    patient_label: str | None = None
    emk: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class TranscriptSegment(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    visit_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    text: str
    is_final: bool = Field(default=True)
    source: str = Field(default="asr")
    start_ms: int | None = None
    end_ms: int | None = None


class Finding(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    visit_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    code: str = Field(index=True)
    severity: str
    title: str
    message: str
    section: str | None = None
    status: str = Field(default="open", index=True)


class EvidenceRef(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    visit_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    kr_id: str
    title: str
    section: str
    fragment: str
    url: str | None = None
    score: float = 0.0
    is_stub: bool = True


class DoctorConfirmation(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    visit_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    scope: str
    confirmed_by: str = "local-doctor"
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class ExportRecord(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    visit_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    export_type: str
    path: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class AuditEvent(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    visit_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    actor: str = "system"
    action: str = Field(index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
