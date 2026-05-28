import {
  AlertTriangle,
  Check,
  Download,
  FileJson,
  FileText,
  Mic,
  MicOff,
  ShieldCheck,
  Stethoscope,
  ClipboardCheck
} from "lucide-react";
import { FormEvent, useMemo, useRef, useState } from "react";
import {
  addTranscript,
  confirmVisit,
  createVisit,
  docxUrl,
  exportText,
  finalizeVisit,
  wsUrl
} from "./lib/api";
import type { ExportText, Finding, VisitState } from "./types";

function severityClass(finding: Finding): string {
  if (finding.status === "resolved") return "ok";
  return finding.severity;
}

const lowerLimbDemo = "У пациента боль в нижних конечностях, правая голень отечна, стопа холодная. Ему 17 лет.";

export function App() {
  const [state, setState] = useState<VisitState | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [socketStatus, setSocketStatus] = useState("offline");
  const [exported, setExported] = useState<ExportText | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  const openFindings = useMemo(
    () => state?.findings.filter((item) => item.status === "open") ?? [],
    [state]
  );
  const criticalCount = openFindings.filter((item) => item.severity === "critical").length;

  async function ensureVisit(): Promise<VisitState> {
    if (state) return state;
    const visit = await createVisit("Локальный прием");
    const next: VisitState = { visit, transcript: [], findings: [], evidence: [] };
    setState(next);
    return next;
  }

  async function submitText(event?: FormEvent) {
    event?.preventDefault();
    const current = await ensureVisit();
    if (!draft.trim()) return;
    setBusy(true);
    try {
      const next = await addTranscript(current.visit.id, draft);
      setState(next);
      setDraft("");
      setExported(null);
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!state) return;
    setBusy(true);
    try {
      const visit = await confirmVisit(state.visit.id);
      setState({ ...state, visit });
    } finally {
      setBusy(false);
    }
  }

  async function finalize() {
    const current = await ensureVisit();
    setBusy(true);
    try {
      const next = await finalizeVisit(current.visit.id);
      setState(next);
    } finally {
      setBusy(false);
    }
  }

  async function downloadText(type: "json" | "html" | "1c") {
    if (!state) return;
    const payload = await exportText(state.visit.id, type);
    setExported(payload);
    const blob = new Blob([payload.content], { type: payload.media_type });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = payload.filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function toggleMic() {
    const current = await ensureVisit();
    if (recording) {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "finalize_recording" }));
      }
      wsRef.current?.close();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      void audioContextRef.current?.close();
      setRecording(false);
      setSocketStatus("offline");
      return;
    }

    const ws = new WebSocket(wsUrl(current.visit.id));
    ws.binaryType = "arraybuffer";
    ws.onopen = async () => {
      setSocketStatus("connected");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, noiseSuppression: true, echoCancellation: true }
      });
      const audioContext = new AudioContext({ sampleRate: 16000 });
      await audioContext.audioWorklet.addModule("/pcm-worklet.js");
      const source = audioContext.createMediaStreamSource(stream);
      const worklet = new AudioWorkletNode(audioContext, "pcm-worklet");
      worklet.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(event.data);
      };
      source.connect(worklet);
      worklet.connect(audioContext.destination);
      streamRef.current = stream;
      audioContextRef.current = audioContext;
      setRecording(true);
    };
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "state") setState(payload.state);
      if (payload.type === "segment_checked") setState(payload.state);
      if (payload.type === "recording_finalized") setState(payload.state);
      if (payload.type === "transcribing") setSocketStatus("transcribing");
      if (payload.type === "ready") setSocketStatus("ready");
    };
    ws.onclose = () => {
      setRecording(false);
      setSocketStatus("offline");
    };
    wsRef.current = ws;
  }

  const emk = state?.visit.emk;

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">
          <Stethoscope size={22} />
          <div>
            <h1>МедЖарвис</h1>
            <span>{focusLabel(emk?.clinical_focus)}</span>
          </div>
        </div>
        <div className="statusline">
          <span className={state?.visit.doctor_confirmed ? "pill ok" : "pill warning"}>
            {state?.visit.doctor_confirmed ? "Подтверждено врачом" : "Черновик"}
          </span>
          <span className={criticalCount ? "pill critical" : "pill ok"}>
            {criticalCount ? `${criticalCount} крит.` : "крит. нет"}
          </span>
          <span className="pill neutral">WS {socketStatus}</span>
        </div>
      </header>

      <section className="workspace">
        <section className="left">
          <form className="dictation" onSubmit={submitText}>
            <div className="toolbar">
              <button type="button" className="iconButton" title="Микрофон" onClick={toggleMic}>
                {recording ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              <button type="button" onClick={() => setDraft(lowerLimbDemo)}>НК пример</button>
              <button type="submit" disabled={busy || !draft.trim()}>Отправить</button>
              <button type="button" onClick={finalize} disabled={busy || !state}>
                <ClipboardCheck size={16} /> Завершить
              </button>
            </div>
            <textarea
              value={draft}
              placeholder="Введите или надиктуйте фрагмент приема"
              onChange={(event) => setDraft(event.target.value)}
            />
          </form>

          <section className="transcript">
            <h2>Диалог</h2>
            <div className="transcriptList">
              {(state?.transcript.length ? state.transcript : ["Новый прием"]).map((item, index) => (
                <p key={`${index}-${item}`}>{item}</p>
              ))}
            </div>
          </section>
        </section>

        <section className="center">
          <div className="sectionHeader">
            <h2>ЭМК</h2>
            <span>{state?.visit.id.slice(0, 8) ?? "не создан"}</span>
          </div>
          <div className="emkGrid">
            <EMKBlock title="Жалобы" items={emk?.complaints} />
            <EMKBlock title="Анамнез" items={emk?.anamnesis} fallback={emk?.allergy ? [`Аллергия: ${emk.allergy}`] : []} />
            <EMKBlock title="Объективно" items={emk?.objective} fallback={emk?.blood_pressure ? [`АД: ${emk.blood_pressure}`] : []} />
            {emk?.clinical_focus === "dental" ? <DentalPanel emk={emk} /> : null}
            {emk?.clinical_focus === "lower_limb" ? <LowerLimbPanel emk={emk} /> : null}
            <section className="panel wide">
              <h3>Диагноз и рекомендации</h3>
              <p className="diagnosis">{emk?.diagnosis.code ?? "-"} {emk?.diagnosis.title ?? ""}</p>
              <p>{emk?.diagnosis.confirmed ? "МКБ подтвержден" : "МКБ ожидает подтверждения"}</p>
              <ul>{emk?.recommendations.map((item) => <li key={item}>{item}</li>)}</ul>
              {emk?.final_summary && <p className="summary">{emk.final_summary}</p>}
            </section>
          </div>
        </section>

        <aside className="right">
          <section className="panel riskPanel">
            <h2><AlertTriangle size={18} /> Контроль</h2>
            <div className="findings">
              {(state?.findings ?? []).map((finding) => (
                <article className={`finding ${severityClass(finding)}`} key={finding.code}>
                  <strong>{finding.title}</strong>
                  <span>{finding.message}</span>
                </article>
              ))}
            </div>
          </section>

          <section className="panel evidence">
            <h2><ShieldCheck size={18} /> КР Минздрава</h2>
            {(state?.evidence ?? []).map((item) => (
              <article key={`${item.kr_id}-${item.section}`}>
                <strong>{item.kr_id}</strong>
                <span>{item.section}</span>
                <p>{item.fragment}</p>
                {item.is_stub && <small>stub provider</small>}
              </article>
            ))}
          </section>

          <section className="panel actions">
            <button onClick={confirm} disabled={!state || busy}>
              <Check size={16} /> Подтвердить
            </button>
            <button onClick={() => downloadText("json")} disabled={!state?.visit.doctor_confirmed}>
              <FileJson size={16} /> JSON
            </button>
            <button onClick={() => downloadText("html")} disabled={!state?.visit.doctor_confirmed}>
              <FileText size={16} /> HTML
            </button>
            <button onClick={() => downloadText("1c")} disabled={!state?.visit.doctor_confirmed}>
              <FileText size={16} /> 1C
            </button>
            <a className={state?.visit.doctor_confirmed ? "downloadLink" : "downloadLink disabled"} href={state ? docxUrl(state.visit.id) : "#"}>
              <Download size={16} /> DOCX
            </a>
            {exported && <small>Экспорт: {exported.filename}</small>}
          </section>
        </aside>
      </section>
    </main>
  );
}

function EMKBlock({ title, items, fallback = [] }: { title: string; items?: string[]; fallback?: string[] }) {
  const rows = [...(items ?? []), ...fallback];
  return (
    <section className="panel">
      <h3>{title}</h3>
      {rows.length ? <ul>{rows.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="empty">-</p>}
    </section>
  );
}

function focusLabel(focus?: string): string {
  if (focus === "dental") return "Стоматология 043/у";
  if (focus === "lower_limb") return "Амбулаторный прием: нижние конечности";
  return "Амбулаторный прием";
}

function DentalPanel({ emk }: { emk: NonNullable<VisitState["visit"]["emk"]> }) {
  return (
    <section className="panel">
      <h3>Стоматология</h3>
      <dl>
        <dt>Зуб FDI</dt><dd>{emk.dental.tooth_fdi ?? "-"}</dd>
        <dt>Одонтограмма</dt><dd>{emk.dental.odontogram_done ? "заполнена" : "-"}</dd>
        <dt>Перкуссия</dt><dd>{emk.dental.percussion ?? "-"}</dd>
        <dt>Термопроба</dt><dd>{emk.dental.thermal_test ?? "-"}</dd>
        <dt>ЭОД</dt><dd>{emk.dental.eod_mka ? `${emk.dental.eod_mka} мкА` : "-"}</dd>
      </dl>
    </section>
  );
}

function LowerLimbPanel({ emk }: { emk: NonNullable<VisitState["visit"]["emk"]> }) {
  return (
    <section className="panel">
      <h3>Нижние конечности</h3>
      <dl>
        <dt>Сторона</dt><dd>{emk.lower_limb.side ?? "-"}</dd>
        <dt>Область</dt><dd>{emk.lower_limb.location ?? "-"}</dd>
        <dt>Отек</dt><dd>{emk.lower_limb.edema ?? "-"}</dd>
        <dt>Кожа</dt><dd>{emk.lower_limb.skin_color ?? "-"} / {emk.lower_limb.skin_temperature ?? "-"}</dd>
        <dt>Пульс стопы</dt><dd>{emk.lower_limb.dorsalis_pedis_pulse ?? "-"}</dd>
        <dt>Чувств.</dt><dd>{emk.lower_limb.sensitivity ?? "-"}</dd>
        <dt>Движения</dt><dd>{emk.lower_limb.movement ?? "-"}</dd>
      </dl>
    </section>
  );
}
