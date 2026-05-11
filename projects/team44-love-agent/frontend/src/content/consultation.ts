// 라운드별 화면(round.*) 문구 — user_messages.md 기준
export const consultationContent = {
  round1: {
    // round.initial_opinions.title — 1라운드 제목
    title: '첫 의견',
    // round.initial_opinions.description — 1라운드 설명
    description: '에이전트들이 각자의 관점에서 상황을 먼저 해석했어요.',
  },
  round2: {
    // round.discussion.title — 2라운드 제목
    title: '토론 과정',
    // round.discussion.description — 2라운드 설명
    description: '서로의 의견을 비교하며 놓친 지점을 보완하고 있어요.',
  },
  round3: {
    // round.final_positions.title — 3라운드 제목
    title: '최종 입장',
    // round.final_positions.description — 3라운드 설명
    description: '토론을 반영해 각 에이전트가 마지막 의견을 정리했어요.',
  },
  supervisorNote: {
    // round.supervisor_note.title — 슈퍼바이저 메모 제목
    title: '정리 메모',
  },
  // round.skipped_agent — 스킵된 에이전트 표시
  skippedAgent: '이번 라운드에서는 이 에이전트의 의견을 건너뛰었어요.',

  // StepBar 전용 라벨 — 짧은 제목 + 한 줄 설명
  steps: {
    analysis: { title: '고민 분석', subtitle: '상황과 감정을 파악해요' },
    round1: { title: '첫 의견', subtitle: '6명이 각자 의견을 내요' },
    round2: { title: '토론 과정', subtitle: '의견을 비교하고 보완해요' },
    round3: { title: '최종 입장', subtitle: '마지막 입장을 정리해요' },
    result: { title: '최종 조언', subtitle: '균형 잡힌 결론을 드려요' },
  },
};
