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


def _has_dental_data(emk: EMK) -> bool:
    return any(
        [
            emk.dental.tooth_fdi,
            emk.dental.odontogram_done,
            emk.dental.percussion,
            emk.dental.thermal_test,
            emk.dental.eod_mka is not None,
        ]
    )


def _has_lower_limb_data(emk: EMK) -> bool:
    lower = emk.lower_limb
    return any(
        [
            lower.side,
            lower.location,
            lower.pain,
            lower.edema,
            lower.skin_color,
            lower.skin_temperature,
            lower.dorsalis_pedis_pulse,
            lower.posterior_tibial_pulse,
            lower.sensitivity,
            lower.movement,
            lower.trauma,
            lower.walking_limit,
        ]
    )


def check_emk_quality(emk: EMK, final: bool = False) -> list[FindingOut]:
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
    if emk.clinical_focus == "dental" or _has_dental_data(emk):
        findings.extend(_check_dental_quality(emk))

    if emk.clinical_focus == "lower_limb" or _has_lower_limb_data(emk):
        findings.extend(_check_lower_limb_quality(emk))
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
    if final or emk.diagnosis.code:
        findings.append(
            _finding(
                "diagnosis.confirm",
                "critical",
                "МКБ-кандидат не подтвержден",
                "Подтвердите или измените диагноз перед подписью.",
                "diagnosis",
                ok=bool(emk.diagnosis.code and emk.diagnosis.confirmed),
                ok_title="МКБ подтвержден",
                ok_message=(
                    f"Подтвержден диагноз {emk.diagnosis.code} {emk.diagnosis.title or ''}."
                ),
            )
        )

    if final:
        findings.append(
            _finding(
                "summary.required",
                "critical",
                "Итог приема не сформирован",
                "После завершения записи нужна суммаризация диалога.",
                "summary",
                ok=bool(emk.final_summary),
                ok_title="Итог приема сформирован",
                ok_message="Финальная суммаризация диалога сохранена в ЭМК.",
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


def _check_dental_quality(emk: EMK) -> list[FindingOut]:
    return [
        _finding(
            "tooth_fdi.required",
            "critical",
            "Не указан зуб FDI",
            "Укажите номер зуба в системе FDI, например 36.",
            "objective",
            ok=bool(emk.dental.tooth_fdi),
            ok_title="Зуб FDI указан",
            ok_message=f"Зуб {emk.dental.tooth_fdi} зафиксирован в стоматологическом статусе.",
        ),
        _finding(
            "odontogram.required",
            "warning",
            "Не заполнена одонтограмма",
            "Отметьте состояние зуба и соседних тканей в одонтограмме.",
            "objective",
            ok=emk.dental.odontogram_done,
            ok_title="Одонтограмма заполнена",
            ok_message="Стоматологический статус содержит отметку одонтограммы.",
        ),
        _finding(
            "percussion.required",
            "warning",
            "Нет данных перкуссии",
            "Для дифференциальной диагностики зафиксируйте перкуссию.",
            "objective",
            ok=bool(emk.dental.percussion),
            ok_title="Перкуссия зафиксирована",
            ok_message=f"Перкуссия: {emk.dental.percussion}.",
        ),
        _finding(
            "thermal.required",
            "warning",
            "Нет термопробы",
            "Добавьте реакцию на холодовую или тепловую пробу.",
            "objective",
            ok=bool(emk.dental.thermal_test),
            ok_title="Термопроба зафиксирована",
            ok_message=f"Термопроба: {emk.dental.thermal_test}.",
        ),
        _finding(
            "eod.required",
            "warning",
            "ЭОД нужен для дифдиагностики",
            "Укажите ЭОД в мкА, если проба выполнена.",
            "objective",
            ok=emk.dental.eod_mka is not None,
            ok_title="ЭОД зафиксирован",
            ok_message=f"ЭОД: {emk.dental.eod_mka} мкА.",
        ),
    ]


def _check_lower_limb_quality(emk: EMK) -> list[FindingOut]:
    lower = emk.lower_limb
    return [
        _finding(
            "lower_limb.location.required",
            "critical",
            "Не уточнена локализация",
            "Для жалоб на нижние конечности нужно указать сторону и область.",
            "objective",
            ok=bool(lower.location and lower.side),
            ok_title="Локализация уточнена",
            ok_message=f"Локализация: {lower.side or '-'}, {lower.location or '-'}.",
        ),
        _finding(
            "lower_limb.pulses.required",
            "critical",
            "Не проверен пульс на стопе",
            "Зафиксируйте пульс на тыльной артерии стопы и/или задней большеберцовой.",
            "objective",
            ok=bool(lower.dorsalis_pedis_pulse or lower.posterior_tibial_pulse),
            ok_title="Пульс на стопе проверен",
            ok_message=(
                "Пульс: "
                f"тыльная артерия стопы - {lower.dorsalis_pedis_pulse or '-'}, "
                f"задняя большеберцовая - {lower.posterior_tibial_pulse or '-'}."
            ),
        ),
        _finding(
            "lower_limb.skin.required",
            "warning",
            "Нет оценки кожи конечности",
            "Уточните цвет и температуру кожи нижней конечности.",
            "objective",
            ok=bool(lower.skin_color or lower.skin_temperature),
            ok_title="Кожа конечности оценена",
            ok_message=(
                f"Цвет: {lower.skin_color or '-'}, температура: {lower.skin_temperature or '-'}."
            ),
        ),
        _finding(
            "lower_limb.neuro.required",
            "warning",
            "Нет неврологического статуса",
            "Уточните чувствительность и движения в конечности.",
            "objective",
            ok=bool(lower.sensitivity or lower.movement),
            ok_title="Неврологический статус уточнен",
            ok_message=(
                f"Чувствительность: {lower.sensitivity or '-'}, "
                f"движения: {lower.movement or '-'}."
            ),
        ),
        _finding(
            "lower_limb.edema.checked",
            "warning",
            "Отек не оценен",
            "Зафиксируйте наличие или отсутствие отека.",
            "objective",
            ok=bool(lower.edema),
            ok_title="Отек оценен",
            ok_message=f"Отек: {lower.edema}.",
        ),
    ]


def blocking_findings(findings: list[FindingOut]) -> list[FindingOut]:
    return [item for item in findings if item.status == "open" and item.severity == "critical"]
