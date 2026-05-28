export type Severity = "critical" | "warning" | "info" | "ok";
export type FindingStatus = "open" | "resolved";

export interface DiagnosisCandidate {
  code: string | null;
  title: string | null;
  confidence: number;
  confirmed: boolean;
}

export interface Prescription {
  name: string;
  dose: string | null;
  frequency: string | null;
  duration: string | null;
}

export interface DentalExam {
  tooth_fdi: string | null;
  odontogram_done: boolean;
  percussion: string | null;
  thermal_test: string | null;
  eod_mka: number | null;
}

export interface LowerLimbExam {
  side: string | null;
  location: string | null;
  pain: string | null;
  edema: string | null;
  skin_color: string | null;
  skin_temperature: string | null;
  dorsalis_pedis_pulse: string | null;
  posterior_tibial_pulse: string | null;
  sensitivity: string | null;
  movement: string | null;
  trauma: string | null;
  walking_limit: string | null;
}

export interface EMK {
  clinical_focus: string;
  age_years: number | null;
  complaints: string[];
  anamnesis: string[];
  objective: string[];
  diagnosis: DiagnosisCandidate;
  dental: DentalExam;
  lower_limb: LowerLimbExam;
  prescriptions: Prescription[];
  recommendations: string[];
  allergy: string | null;
  blood_pressure: string | null;
  final_summary: string | null;
}

export interface Finding {
  code: string;
  severity: Severity;
  title: string;
  message: string;
  section: string | null;
  status: FindingStatus;
}

export interface Evidence {
  kr_id: string;
  title: string;
  section: string;
  fragment: string;
  url: string | null;
  score: number;
  is_stub: boolean;
}

export interface Visit {
  id: string;
  created_at: string;
  updated_at: string;
  status: string;
  doctor_confirmed: boolean;
  patient_label: string | null;
  emk: EMK;
}

export interface VisitState {
  visit: Visit;
  transcript: string[];
  findings: Finding[];
  evidence: Evidence[];
}

export interface ExportText {
  export_type: string;
  filename: string;
  content: string;
  media_type: string;
}

export interface HealthStatus {
  ok: boolean;
  gpu: {
    ok: boolean;
    name?: string;
    total_mb?: number;
    free_mb?: number;
    driver?: string;
    reason?: string;
  };
  llm: {
    ok: boolean;
    url: string;
    model: string;
    required: boolean;
  };
  asr: {
    model: string;
    language: string;
    compute_type: string;
    device: string;
    preload: boolean;
    beam_size: number;
    best_of: number;
    temperature: number;
    condition_on_previous_text: boolean;
    initial_prompt_set: boolean;
    hotwords_set: boolean;
  };
}
