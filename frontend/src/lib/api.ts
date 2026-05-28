import type { ExportText, Visit, VisitState } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export async function createVisit(patientLabel?: string): Promise<Visit> {
  return parse<Visit>(
    await fetch(`${API_BASE}/api/visits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_label: patientLabel ?? null })
    })
  );
}

export async function getVisitState(visitId: string): Promise<VisitState> {
  return parse<VisitState>(await fetch(`${API_BASE}/api/visits/${visitId}`));
}

export async function addTranscript(visitId: string, text: string): Promise<VisitState> {
  return parse<VisitState>(
    await fetch(`${API_BASE}/api/visits/${visitId}/transcript`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source: "manual" })
    })
  );
}

export async function confirmVisit(visitId: string): Promise<Visit> {
  return parse<Visit>(
    await fetch(`${API_BASE}/api/visits/${visitId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "visit", payload: { ui: "doctor_confirmed" } })
    })
  );
}

export async function finalizeVisit(visitId: string): Promise<VisitState> {
  return parse<VisitState>(
    await fetch(`${API_BASE}/api/visits/${visitId}/finalize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    })
  );
}

export async function exportText(visitId: string, exportType: "json" | "html" | "1c"): Promise<ExportText> {
  return parse<ExportText>(await fetch(`${API_BASE}/api/visits/${visitId}/exports/${exportType}`));
}

export function docxUrl(visitId: string): string {
  return `${API_BASE}/api/visits/${visitId}/exports/docx`;
}

export function wsUrl(visitId: string): string {
  const url = new URL(API_BASE);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/visits/${visitId}/audio`;
  return url.toString();
}
