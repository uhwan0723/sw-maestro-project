export type Workspace = {
  id: number
  name: string
  description: string
  created_at: string
}

export type RawDocument = {
  id: number
  workspace_id: number
  filename: string
  document_type: string
  source_type: string
  source_url: string
  external_id: string
  content: string
  created_at: string
}

export type KnowledgeCard = {
  id: number
  workspace_id: number
  source_document_id: number
  source_chunk_id: number
  card_type: string
  title: string
  summary: string
  evidence_quote: string
  keywords: string[]
  tags: string[]
  status: string
  confidence: string
  created_at: string
  updated_at: string
}

export type GraphNode = {
  id: string
  type: "document" | "card"
  label: string
  document_type?: string
  card_type?: string
  status?: string
  confidence?: string
}

export type GraphLink = {
  source: string
  target: string
  type: string
  label: string
  confidence?: string
}

export type KnowledgeGraph = {
  nodes: GraphNode[]
  links: GraphLink[]
}

export type WorkflowDefinition = {
  id: string
  name: string
  owner: string
  status: "implemented" | "remote_connected" | "extension_slot" | string
  purpose: string
  entrypoint: string
  workflow_file: string
  nodes: string[]
  input_contract: string
  output_contract: string
  notes: string
}

export type WorkflowLink = {
  source: string
  target: string
  label: string
}

export type WorkflowRegistry = {
  version: string
  runtime: string
  policy: string
  flows: WorkflowDefinition[]
  links: WorkflowLink[]
}

export type ReviewTarget = {
  card_id: number
  relation_id?: number | null
  reason?: string
  reasons?: string[]
  priority?: "high" | "medium" | "low" | string
  card_type: string
  title: string
  issue: string
  suggestion: string
}

export type SearchResponse = {
  cards: KnowledgeCard[]
  chunks: Array<{
    id: number
    document_id: number
    workspace_id: number
    chunk_index: number
    content: string
    token_estimate: number
    created_at: string
  }>
}

export type LlmAnswer = {
  query?: string
  answer: string
  confidence: string
  evidence_cards: Array<{
    card_id: number
    title: string
    source_document: string
    evidence_quote: string
  }>
  evidence_chunks: Array<{
    chunk_id: number
    source_document: string
    quote: string
  }>
  relation_evidence: Array<{
    relation_id: number
    source_card_id: number
    target_card_id: number
    relation_type: string
    reason: string
    confidence: string
  }>
  missing_evidence: string[]
}

export type ReviewResult = {
  workspace_id?: number
  total_cards: number
  reviewed_count: number
  review_targets: ReviewTarget[]
  quality_summary: string
  target_count?: number
  targets?: ReviewTarget[]
  summary?: {
    needs_review: number
    low_confidence: number
    weak_evidence?: number
    contradictions?: number
  }
}

export type SourcePayload = {
  source_type: string
  source_url: string
  external_id: string
  title: string
  content: string
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(readApiError(detail) || `${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

export async function apiFormRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(readApiError(detail) || `${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

function readApiError(detail: string): string {
  if (!detail) return ""
  try {
    const parsed = JSON.parse(detail) as { detail?: unknown }
    if (typeof parsed.detail === "string") return parsed.detail
    if (Array.isArray(parsed.detail)) return parsed.detail.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join("; ")
  } catch {
    return detail
  }
  return detail
}
