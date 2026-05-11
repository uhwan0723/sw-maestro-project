// 상담 진행 상태(status.*) 문구 — ConsultationStatus 값과 1:1 매핑, user_messages.md 기준
export const statusContent: Record<string, { short: string; description: string }> = {
  // status.pending
  pending: { short: '상담 준비 중', description: '입력한 고민을 상담 흐름에 맞게 준비하고 있어요.' },
  // status.analyzing
  analyzing: { short: '고민 분석 중', description: '관계 상태, 감정, 핵심 이슈를 먼저 정리하고 있어요.' },
  // status.round_1_running
  round_1_running: { short: '에이전트 의견 모으는 중', description: '6명의 에이전트가 각자의 관점에서 첫 의견을 만들고 있어요.' },
  // status.summary_1_running
  summary_1_running: { short: '쟁점 정리 중', description: '나온 의견에서 공통점과 갈리는 지점을 정리하고 있어요.' },
  // status.round_2_running
  round_2_running: { short: '에이전트 토론 중', description: '서로 다른 의견을 비교하며 더 현실적인 조언을 찾고 있어요.' },
  // status.classify_2_running
  classify_2_running: { short: '토론 흐름 정리 중', description: '합의된 부분과 더 볼 필요가 있는 부분을 나누고 있어요.' },
  // status.round_3_running
  round_3_running: { short: '최종 입장 정리 중', description: '각 에이전트가 마지막 입장을 다듬고 있어요.' },
  // status.summarizing
  summarizing: { short: '결론 작성 중', description: '토론 결과를 바탕으로 실행 가능한 조언을 정리하고 있어요.' },
  // status.completed
  completed: { short: '상담 완료', description: '지금 상황에서 가장 균형 잡힌 방향을 정리했어요.' },
  // status.terminated
  terminated: { short: '상담 정리 완료', description: '가능한 범위 안에서 안전하게 상담을 마무리했어요.' },
  // status.failed
  failed: { short: '상담을 완료하지 못했어요', description: '일시적인 문제로 결과를 만들지 못했어요. 잠시 뒤 다시 시도해주세요.' },
};
