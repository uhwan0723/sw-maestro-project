export type SectorCode = "semiconductor" | "pharmaceutical";

export interface WarningMessage {
  code: string;
  message: string;
}

export interface SourceInfo {
  title: string;
  url: string;
  provider: string;
  published_at: string;
}

export interface KeyEvidence {
  title: string;
  description: string;
  source: SourceInfo | null;
}

export interface SectorAnalysisResponse {
  sector: SectorCode | null;
  beginner_summary: string;
  key_evidence: KeyEvidence[];
  confidence: number;
  caution: string;
  warnings: WarningMessage[];
}

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export interface ChatRequest {
  message: string;
  sector?: SectorCode | null;
  session_id?: string | null;
  history?: ChatTurn[];
}

export interface ChatResponse {
  request_type: "sector_analysis" | "term_explanation" | "out_of_scope";
  answer: string;
  safety_notice: string | null;
  warnings: WarningMessage[];
  session_id: string | null;
}
