// 오류(error.*) 및 종료(termination.*) 문구 — user_messages.md 기준

// ErrorMessage, EmptyState 컴포넌트 fallback 문구
export const errorContent = {
  // 기본 오류 메시지 (ErrorMessage 컴포넌트)
  generic: '알 수 없는 문제가 발생했어요. 잠시 뒤 다시 시도해주세요.',
  // 빈 상태 메시지 (EmptyState 컴포넌트)
  empty: '데이터가 없습니다.',
  // action.retry — 재시도 버튼
  retryButton: '다시 시도',
};

// error.* — ErrorCode별 사용자 오류 문구
export const errorMessages: Record<string, string> = {
  // error.llm_timeout
  llm_timeout: '일부 에이전트의 응답이 늦어져 해당 의견을 건너뛰었어요.',
  // error.llm_rate_limit
  llm_rate_limit: '요청이 잠시 몰려 상담이 지연되고 있어요. 조금 뒤 다시 시도해주세요.',
  // error.json_parse_failed
  json_parse_failed: '일부 응답을 화면에 맞게 정리하지 못해 해당 의견을 제외했어요.',
  // error.schema_violation
  schema_violation: '일부 응답 형식이 맞지 않아 해당 의견을 제외했어요.',
  // error.persona_drift
  persona_drift: '일부 에이전트 의견이 역할 기준과 맞지 않아 제외했어요.',
  // error.safety_blocked
  safety_blocked: '안전한 상담 범위를 벗어난 내용이 있어 답변을 제한했어요.',
  // error.workflow_timeout
  workflow_timeout: '상담 시간이 너무 길어져 완료하지 못했어요. 잠시 뒤 다시 시도해주세요.',
  // error.unknown
  unknown: '알 수 없는 문제가 발생했어요. 잠시 뒤 다시 시도해주세요.',
};

// termination.* — TerminationReason별 사용자 문구
export const terminationContent: Record<string, string> = {
  // termination.normal
  normal: '상담이 정상적으로 완료됐어요.',
  // termination.consensus_reached
  consensus_reached: '에이전트들이 충분히 비슷한 결론에 도달해 토론을 일찍 마무리했어요.',
  // termination.repetition_detected
  repetition_detected: '같은 의견이 반복되어 핵심 결론을 중심으로 상담을 정리했어요.',
  // termination.round_limit_exceeded
  round_limit_exceeded: '정해진 토론 범위 안에서 가능한 결론을 정리했어요.',
  // termination.persona_breakdown
  persona_breakdown: '일부 에이전트 의견이 역할 기준에서 벗어나 안전하게 제외하고 상담을 정리했어요.',
  // termination.safety_refused
  safety_refused:
    '이 내용은 안전한 상담 범위를 벗어나 자세한 답변을 제공하기 어려워요. 필요하다면 신뢰할 수 있는 사람이나 전문가에게 도움을 요청해주세요.',
  // termination.timeout
  timeout: '상담 시간이 길어져 지금까지 정리된 내용으로 마무리했어요.',
  // termination.internal_error
  internal_error: '내부 문제로 상담을 끝까지 진행하지 못했어요. 잠시 뒤 다시 시도해주세요.',
};
