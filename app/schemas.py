from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LowerLimbExam(BaseModel):
    side: str | None = None
    location: str | None = None
    pain: str | None = None
    edema: str | None = None
    skin_color: str | None = None
    skin_temperature: str | None = None
    dorsalis_pedis_pulse: str | None = None
    posterior_tibial_pulse: str | None = None
    sensitivity: str | None = None
    movement: str | None = None
    trauma: str | None = None
    walking_limit: str | None = None


class DiagnosisCandidate(BaseModel):
    code: str | None = None
    title: str | None = None
    confidence: float = 0.0
    confirmed: bool = False


class Prescription(BaseModel):
    name: str
    dose: str | None = None
    frequency: str | None = None
    duration: str | None = None


class DentalExam(BaseModel):
    tooth_fdi: str | None = None
    odontogram_done: bool = False
    percussion: str | None = None
    thermal_test: str | None = None
    eod_mka: int | None = None


class EMK(BaseModel):
    clinical_focus: str = "general"
    age_years: int | None = None
    complaints: list[str] = Field(default_factory=list)
    anamnesis: list[str] = Field(default_factory=list)
    objective: list[str] = Field(default_factory=list)
    diagnosis: DiagnosisCandidate = Field(default_factory=DiagnosisCandidate)
    dental: DentalExam = Field(default_factory=DentalExam)
    lower_limb: LowerLimbExam = Field(default_factory=LowerLimbExam)
    prescriptions: list[Prescription] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    allergy: str | None = None
    blood_pressure: str | None = None
    final_summary: str | None = None


class FindingOut(BaseModel):
    code: str
    severity: Literal["critical", "warning", "info", "ok"]
    title: str
    message: str
    section: str | None = None
    status: Literal["open", "resolved"] = "open"


class EvidenceOut(BaseModel):
    kr_id: str
    title: str
    section: str
    fragment: str
    url: str | None = None
    score: float
    is_stub: bool = True


class VisitCreate(BaseModel):
    patient_label: str | None = None


class VisitOut(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: str
    doctor_confirmed: bool
    patient_label: str | None
    emk: EMK


class TranscriptIn(BaseModel):
    text: str
    source: str = "manual"


class ConfirmationIn(BaseModel):
    scope: str = "visit"
    payload: dict[str, Any] = Field(default_factory=dict)


class VisitState(BaseModel):
    visit: VisitOut
    transcript: list[str]
    findings: list[FindingOut]
    evidence: list[EvidenceOut]


class ExportResponse(BaseModel):
    export_type: str
    filename: str
    content: str
    media_type: str
