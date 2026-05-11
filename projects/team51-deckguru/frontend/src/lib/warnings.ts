type WarningMessage = {
  title: string;
  description: string;
  detail?: string;
};

const WARNING_MESSAGE_BY_CODE: Record<string, WarningMessage> = {
  insufficient_data_after_patch: {
    title: '패치 직후라 통계가 충분하지 않을 수 있습니다',
    description:
      '새 패치 반영 직후에는 표본이 적어 추천이 빠르게 바뀔 수 있습니다. 출처와 함께 실제 게임 상황을 한 번 더 확인해 주세요.',
  },
  data_may_be_insufficient_after_patch: {
    title: '패치 직후라 통계가 충분하지 않을 수 있습니다',
    description:
      '새 패치 반영 직후에는 표본이 적어 추천이 빠르게 바뀔 수 있습니다. 출처와 함께 실제 게임 상황을 한 번 더 확인해 주세요.',
  },
  all_decks_filtered: {
    title: '근거가 부족한 추천을 제외했습니다',
    description:
      '검증 단계에서 충분한 기물 또는 출처 근거를 찾지 못한 덱을 걸렀습니다. 질문에 핵심 기물, 보유 아이템, 원하는 운영 방향을 더 넣으면 결과가 나아질 수 있습니다.',
  },
  intent_classification_failed: {
    title: '질문 의도를 확실히 분류하지 못했습니다',
    description:
      '질문이 지원 범위와 맞는지 판단하는 단계에서 문제가 있었습니다. 덱 추천, 운영법, 아이템 전환처럼 원하는 답변 유형을 더 직접적으로 적어 주세요.',
  },
  intent_classification_fallback: {
    title: '질문 의도를 보수적으로 분류했습니다',
    description:
      'AI 분류가 실패해 규칙 기반 방식으로 질문 유형을 추정했습니다. 답변이 기대와 다르면 원하는 결과 유형을 더 구체적으로 적어 주세요.',
  },
  live_research_disabled_by_env: {
    title: '외부 실시간 검색이 꺼져 있습니다',
    description:
      '현재 환경에서는 외부 메타 사이트를 직접 확인하지 않고 내부 데이터 기준으로만 답변했습니다. 최신성이 중요한 질문은 출처를 함께 확인해 주세요.',
  },
  live_research_failed: {
    title: '외부 실시간 검색을 완료하지 못했습니다',
    description:
      '외부 출처를 확인하는 중 오류가 발생해 내부 데이터와 확보된 근거만으로 답변했습니다. 최신 메타와 일부 차이가 있을 수 있습니다.',
  },
  live_research_no_facts: {
    title: '외부 출처에서 추가 근거를 찾지 못했습니다',
    description:
      '실시간 검색은 시도했지만 추천에 반영할 만한 구체적인 사실을 찾지 못했습니다. 결과의 출처와 신뢰도를 함께 확인해 주세요.',
  },
  patch_version_fallback: {
    title: '직전 패치 데이터를 함께 참고했습니다',
    description:
      '현재 패치 데이터가 부족해 이전 패치의 정보를 일부 사용했습니다. 최근 밸런스 변경이 큰 덱은 실제 성능과 차이가 날 수 있습니다.',
  },
  rag_avg_score_low: {
    title: '관련 근거 매칭 점수가 낮습니다',
    description:
      '질문과 내부 메타 데이터가 충분히 강하게 맞지 않아 추천 신뢰도가 낮을 수 있습니다. 티어, 선호 덱, 핵심 기물, 아이템처럼 조건을 더 구체적으로 입력하면 정확도가 올라갑니다.',
  },
  research_extract_timeout_fallback: {
    title: '외부 근거 정리에 시간이 부족했습니다',
    description:
      '수집한 외부 내용을 정리하는 단계가 제한 시간을 넘겨 일부 문장만 추려 답변했습니다. 세부 근거가 충분하지 않을 수 있습니다.',
  },
  research_plan_timeout_fallback: {
    title: '외부 검색 계획을 간소화했습니다',
    description:
      '외부 출처를 어떤 순서로 확인할지 정하는 단계가 지연되어 기본 검색 흐름으로 진행했습니다. 일부 출처 확인이 제한됐을 수 있습니다.',
  },
  research_skipped_no_whitelist: {
    title: '허용되지 않은 외부 출처는 확인하지 않았습니다',
    description:
      '안전한 출처 목록에 없는 페이지는 수집하지 않았습니다. 추천은 허용된 출처와 내부 데이터 기준으로 생성되었습니다.',
  },
  research_truncated: {
    title: '외부 정보 수집이 일부만 완료되었습니다',
    description:
      '제한 시간 안에 모든 외부 출처를 확인하지 못했습니다. 답변은 확보된 정보 기준이며 최신 메타가 일부 빠졌을 수 있습니다.',
  },
  single_source: {
    title: '참고한 외부 출처가 하나뿐입니다',
    description:
      '여러 출처로 교차 확인하지 못해 특정 사이트의 관점이 더 크게 반영됐을 수 있습니다. 중요한 선택이라면 다른 메타 사이트와도 비교해 주세요.',
  },
};

const TOOL_NAME_LABEL: Record<string, string> = {
  fetch_page: '외부 페이지',
  web_search: '웹 검색',
  youtube_transcript: '영상 자막',
};

const TOOL_FAILURE_REASON_MESSAGE: Record<string, string> = {
  empty_page_text:
    '페이지가 빈 본문을 반환했거나 브라우저 렌더링이 필요한 구조라 서버에서 텍스트를 추출하지 못했습니다.',
  url_not_allowed_or_robots_blocked:
    '허용된 출처가 아니거나 robots.txt 정책 때문에 서버에서 페이지를 읽지 않았습니다.',
};

export function formatWarningMessage(warning: string): WarningMessage {
  const staticMessage = WARNING_MESSAGE_BY_CODE[warning];

  if (staticMessage) {
    return staticMessage;
  }

  const deckFilterMessage = formatDeckFilterWarning(warning);

  if (deckFilterMessage) {
    return deckFilterMessage;
  }

  const toolFailureMessage = formatToolFailureWarning(warning);

  if (toolFailureMessage) {
    return toolFailureMessage;
  }

  return {
    title: '확인이 필요한 안내가 있습니다',
    description:
      '추천 품질이나 데이터 수집 상태와 관련된 추가 안내가 내려왔습니다. 결과의 신뢰도와 출처를 함께 확인해 주세요.',
  };
}

function formatDeckFilterWarning(warning: string): WarningMessage | null {
  const prefix = 'deck_filtered_';
  const suffix = '_insufficient_units';

  if (!warning.startsWith(prefix) || !warning.endsWith(suffix)) {
    return null;
  }

  const deckName = warning.slice(prefix.length, -suffix.length);

  return {
    title: '근거가 부족한 덱을 추천에서 제외했습니다',
    description:
      '검증 가능한 핵심 기물이 충분하지 않아 해당 덱을 결과에서 제외했습니다. 비슷한 조건의 다른 덱을 우선 참고해 주세요.',
    detail: deckName ? `제외된 덱: ${deckName}` : undefined,
  };
}

function formatToolFailureWarning(warning: string): WarningMessage | null {
  const [toolName, reason, ...detailParts] = warning
    .split(':')
    .map((part) => part.trim());

  if (!toolName?.endsWith('_failed')) {
    return null;
  }

  const baseToolName = toolName.replace(/_failed$/, '');
  const toolLabel = TOOL_NAME_LABEL[baseToolName] ?? '외부 정보';
  const reasonDescription =
    TOOL_FAILURE_REASON_MESSAGE[reason] ??
    '외부 정보를 확인하는 중 오류가 발생했습니다.';
  const detail = getReadableFailureDetail(detailParts);

  return {
    title: `${toolLabel} 확인에 실패했습니다`,
    description: `${reasonDescription} 해당 출처는 추천 근거에 충분히 반영되지 않았을 수 있습니다.`,
    detail,
  };
}

function getReadableFailureDetail(detailParts: string[]): string | undefined {
  const detail = detailParts.join(':').trim();

  if (!detail) {
    return undefined;
  }

  try {
    const url = new URL(detail);

    return `대상 URL: ${url.href}`;
  } catch {
    return undefined;
  }
}
