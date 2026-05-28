from __future__ import annotations

from app.schemas import EMK, FindingOut


def _finding(
    code: str,
    severity: str,
    title: str,
    message: str,
    section: str,
    ok: bool = False,
    ok_title: str | None = None,
    ok_message: str | None = None,
) -> FindingOut:
    return FindingOut(
        code=code,
        severity="ok" if ok else severity,  # type: ignore[arg-type]
        title=ok_title if ok and ok_title else title,
        message=ok_message if ok and ok_message else message,
        section=section,
        status="resolved" if ok else "open",
    )


def check_emk_quality(emk: EMK) -> list[FindingOut]:
    findings: list[FindingOut] = []

    findings.append(
        _finding(
            "complaints.required",
            "critical",
            "Жалобы не заполнены",
            "Для 043/у нужно зафиксировать жалобы пациента.",
            "complaints",
            ok=bool(emk.complaints),
            ok_title="Жалобы заполнены",
            ok_message="В карте есть структурированные жалобы пациента.",
        )
    )
    findings.append(
        _finding(
            "tooth_fdi.required",
            "critical",
            "Не указан зуб FDI",
            "Укажите номер зуба в системе FDI, например 36.",
            "objective",
            ok=bool(emk.dental.tooth_fdi),
            ok_title="Зуб FDI указан",
            ok_message=f"Зуб {emk.dental.tooth_fdi} зафиксирован в стоматологическом статусе.",
        )
    )
    findings.append(
        _finding(
            "odontogram.required",
            "warning",
            "Не заполнена одонтограмма",
            "Отметьте состояние зуба и соседних тканей в одонтограмме.",
            "objective",
            ok=emk.dental.odontogram_done,
            ok_title="Одонтограмма заполнена",
            ok_message="Стоматологический статус содержит отметку одонтограммы.",
        )
    )
    findings.append(
        _finding(
            "percussion.required",
            "warning",
            "Нет данных перкуссии",
            "Для дифференциальной диагностики зафиксируйте перкуссию.",
            "objective",
            ok=bool(emk.dental.percussion),
            ok_title="Перкуссия зафиксирована",
            ok_message=f"Перкуссия: {emk.dental.percussion}.",
        )
    )
    findings.append(
        _finding(
            "thermal.required",
            "warning",
            "Нет термопробы",
            "Добавьте реакцию на холодовую или тепловую пробу.",
            "objective",
            ok=bool(emk.dental.thermal_test),
            ok_title="Термопроба зафиксирована",
            ok_message=f"Термопроба: {emk.dental.thermal_test}.",
        )
    )
    findings.append(
        _finding(
            "eod.required",
            "warning",
            "ЭОД нужен для дифдиагностики",
            "Укажите ЭОД в мкА, если проба выполнена.",
            "objective",
            ok=emk.dental.eod_mka is not None,
            ok_title="ЭОД зафиксирован",
            ok_message=f"ЭОД: {emk.dental.eod_mka} мкА.",
        )
    )
    findings.append(
        _finding(
            "allergy.required",
            "critical",
            "Аллергия не уточнена",
            "Перед назначениями нужно зафиксировать аллергоанамнез.",
            "anamnesis",
            ok=bool(emk.allergy),
            ok_title="Аллергоанамнез уточнен",
            ok_message=f"Аллергия: {emk.allergy}.",
        )
    )
    findings.append(
        _finding(
            "bp.required",
            "warning",
            "АД не измерено",
            "Зафиксируйте артериальное давление до вмешательства.",
            "objective",
            ok=bool(emk.blood_pressure),
            ok_title="АД зафиксировано",
            ok_message=f"АД: {emk.blood_pressure}.",
        )
    )
    findings.append(
        _finding(
            "diagnosis.confirm",
            "critical",
            "МКБ-кандидат не подтвержден",
            "Подтвердите или измените диагноз перед подписью.",
            "diagnosis",
            ok=bool(emk.diagnosis.code and emk.diagnosis.confirmed),
            ok_title="МКБ подтвержден",
            ok_message=f"Подтвержден диагноз {emk.diagnosis.code} {emk.diagnosis.title or ''}.",
        )
    )

    for idx, prescription in enumerate(emk.prescriptions, start=1):
        ok = bool(prescription.dose and prescription.frequency and prescription.duration)
        findings.append(
            _finding(
                f"prescription.{idx}.complete",
                "critical",
                "Назначение без дозировки",
                f"Для '{prescription.name}' нужны дозировка, кратность и длительность.",
                "prescriptions",
                ok=ok,
                ok_title="Назначение заполнено",
                ok_message=(
                    f"Для '{prescription.name}' указаны дозировка, кратность и длительность."
                ),
            )
        )

    return findings


def blocking_findings(findings: list[FindingOut]) -> list[FindingOut]:
    return [item for item in findings if item.status == "open" and item.severity == "critical"]
