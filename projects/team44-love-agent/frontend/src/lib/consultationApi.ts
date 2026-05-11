import type { BackendConsultationResponse } from './consultationMapper';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/$/, '');

export interface BackendStartResponse {
  consultation_id: string;
  status: BackendConsultationResponse['status'];
}

export interface BackendStreamEvent {
  consultation_id: string;
  sequence: number;
  event_type:
    | 'status_changed'
    | 'analysis_completed'
    | 'agent_message_added'
    | 'supervisor_note_added'
    | 'error_occurred'
    | 'completed';
  payload: Record<string, unknown>;
  emitted_at: string;
}

export async function createConsultation(userQuestion: string, consultationId: string) {
  const response = await fetch(`${API_BASE_URL}/consultations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      consultation_id: consultationId,
      user_question: userQuestion,
      language: 'ko-KR',
      client_meta: {
        submitted_at: new Date().toISOString(),
        user_agent: typeof navigator === 'undefined' ? null : navigator.userAgent,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`상담 요청을 시작하지 못했어요. (${response.status})`);
  }

  return (await response.json()) as BackendStartResponse;
}

export async function getConsultation(consultationId: string) {
  const response = await fetch(`${API_BASE_URL}/consultations/${consultationId}`);
  if (!response.ok) {
    throw new Error(`상담 정보를 불러오지 못했어요. (${response.status})`);
  }
  return (await response.json()) as BackendConsultationResponse;
}

export function openConsultationEventSource(consultationId: string, afterSequence = 0) {
  const url = new URL(`${API_BASE_URL}/consultations/${consultationId}/events`);
  if (afterSequence > 0) {
    url.searchParams.set('after_sequence', String(afterSequence));
  }
  return new EventSource(url.toString());
}
