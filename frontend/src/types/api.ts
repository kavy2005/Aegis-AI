export interface User {
  id: number;
  email: string;
  full_name?: string | null;
}

export interface Patient {
  id: number;
  age?: number | null;
  sex?: string | null;
  pregnant?: boolean | null;
  known_conditions?: string | null;
  medications?: string | null;
  allergies?: string | null;
  lifestyle_notes?: string | null;
}

export interface ExtractedParameter {
  id?: number;
  raw_label: string;
  canonical_parameter?: string | null;
  value?: number | null;
  unit?: string | null;
  reference_low?: number | null;
  reference_high?: number | null;
  reference_source?: string | null;
  flag?: 'normal' | 'high' | 'low' | 'unrecognized' | null;
  severity?: number | null;
}

export interface ReportUploadResponse {
  report_id: number;
  filename: string;
  raw_text_preview: string;
  parameters_detected: number;
  parameters: ExtractedParameter[];
}

export interface RiskAssessment {
  score: number;
  level: number;
  label: string;
  abnormal_count: number;
  critical_breach: boolean;
  summary: string;
}

export interface ExplanationItem {
  parameter: string;
  value: number;
  unit?: string | null;
  flag: string;
  why_it_matters: string;
}

export interface Explanation {
  summary: string;
  abnormal_findings: string[];
  risk_level: number;
  explanation: ExplanationItem[];
  recommended_next_steps: string[];
  urgent_warning?: string | null;
  source?: string;
}

export interface ReportAnalysisResponse {
  report_id: number;
  filename?: string | null;
  raw_text_preview?: string | null;
  risk: RiskAssessment;
  parameters: ExtractedParameter[];
  explanation: Explanation;
  disclaimer: string;
}

export interface ReportSummary {
  id: number;
  filename: string;
  uploaded_at: string;
  is_demo: boolean;
}

export interface HistoryPoint {
  report_id: number;
  date: string;
  level: number;
  score: number;
  parameters: Record<string, number>;
}

export interface MLPredictResponse {
  model_available: boolean;
  predicted_level?: number | null;
  probabilities?: Record<string, number> | null;
  top_contributors?: { feature: string; contribution: number }[] | null;
  message?: string | null;
}

export interface ParameterCorrection {
  raw_label: string;
  canonical_parameter?: string | null;
  value: number;
  unit?: string | null;
}
