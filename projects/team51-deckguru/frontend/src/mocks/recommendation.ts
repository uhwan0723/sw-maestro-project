import type { RecommendationResponse } from '@/lib/schema';

export const mockRecommendDeckResponse: RecommendationResponse = {
  request_id: 'mock-recommend-deck-001',
  patch_version: '14.9',
  intent: 'recommend_deck',
  meta_summary:
    '14.9 패치에서는 정밀 계열과 안정적인 중반 전환 덱이 골드 구간에서 쓰기 좋습니다. 초반 체력 관리가 쉽고, 핵심 아이템 의존도가 과하지 않은 조합을 우선 추천합니다.',
  decks: [
    {
      name: '정밀 리롤',
      difficulty: 'easy',
      core_units: ['정밀의 사도', '기계 학자', '광신도', '라이트브링어'],
      key_items: ['구인수의 격노검', '최후의 속삭임', '정의의 손'],
      augment_direction: '정밀 시너지 강화 또는 공격 속도, 전투 지속력 계열',
      playbook: [
        {
          phase: 'early',
          instruction: '초반에는 정밀 기물과 곡궁 계열 아이템을 모으며 체력을 보존합니다.',
        },
        {
          phase: 'mid',
          instruction: '6레벨 전후 핵심 기물 2성을 맞추고, 겹치는 유저 수를 확인합니다.',
        },
        {
          phase: 'late',
          instruction: '8레벨 이후 보조 시너지를 추가하고 남는 아이템을 보조 딜러에게 줍니다.',
        },
      ],
      good_conditions: ['초반에 곡궁이 나왔을 때', '정밀 기물이 자연스럽게 잡힐 때'],
      avoid_conditions: ['같은 정밀 유저가 2명 이상일 때'],
      fallback_plan: '정밀 기물이 부족하면 라이트브링어 중심 안정형 조합으로 전환합니다.',
      rationale:
        '운영 난이도가 낮고 중반 안정화가 쉬워 골드 구간에서 순방을 노리기 좋습니다.',
    },
    {
      name: '사이버시티 9코',
      difficulty: 'hard',
      core_units: ['사이버시티 챔피언', '9코스트 정밀', '어둠의 화신'],
      key_items: ['구인수의 격노검', '거인 학살자', '최후의 속삭임'],
      augment_direction: '후반 밸류와 고코스트 유닛 확보를 돕는 경제 계열',
      playbook: [
        {
          phase: 'early',
          instruction: '초반 연승이 가능할 때만 체력과 골드를 동시에 관리합니다.',
        },
        {
          phase: 'mid',
          instruction: '7레벨까지 큰 리롤 없이 버티며 핵심 아이템을 보존합니다.',
        },
        {
          phase: 'late',
          instruction: '8레벨 이후 고코스트 유닛을 찾아 최종 밸류를 올립니다.',
        },
      ],
      good_conditions: ['초반 연승이 강할 때', '경제 증강체를 빠르게 잡았을 때'],
      avoid_conditions: ['초반 체력이 크게 낮을 때', '아이템 완성이 늦을 때'],
      fallback_plan: '체력이 부족하면 8레벨 고밸류 조합 대신 중반 완성 덱으로 마무리합니다.',
      rationale:
        '고점은 높지만 운영 난이도가 있어 안정형 덱 이후의 보조 선택지로 적합합니다.',
    },
  ],
  sources: [
    {
      title: '14.9 메타 덱 요약',
      url: 'https://example.com/tft/14-9-meta-decks',
      published_at: '2026-05-04T03:00:00Z',
      snippet: '정밀 계열은 14.9 패치에서 안정적인 중반 운영 선택지로 언급됩니다.',
      source_kind: 'meta_site',
    },
  ],
  confidence: 'medium',
  warnings: [],
  generated_at: '2026-05-07T09:00:00Z',
};

export const mockDeckPlaystyleResponse: RecommendationResponse = {
  request_id: 'mock-deck-playstyle-001',
  patch_version: '14.9',
  intent: 'deck_playstyle',
  meta_summary:
    '현재 많이 쓰이는 정밀 리롤은 초중반 안정성이 장점인 덱입니다. 빠른 완성보다 체력 보존과 겹치는 유저 확인이 중요하며, 후반에는 보조 시너지로 부족한 딜과 탱킹을 보완합니다.',
  decks: [
    {
      name: '정밀 리롤 운영',
      difficulty: 'easy',
      core_units: ['정밀의 사도', '기계 학자', '광신도', '라이트브링어'],
      key_items: ['구인수의 격노검', '최후의 속삭임', '정의의 손'],
      augment_direction: '정밀 강화, 공격 속도, 유지력 보강 계열',
      playbook: [
        {
          phase: 'early',
          instruction: '초반에는 강한 2성 유닛을 쓰며 정밀 기물은 벤치에 모읍니다.',
        },
        {
          phase: 'mid',
          instruction: '6레벨에서 핵심 유닛을 찾고, 겹치면 과한 리롤을 피합니다.',
        },
        {
          phase: 'late',
          instruction: '8레벨에 도달하면 라이트브링어와 탱커를 추가해 전열을 보강합니다.',
        },
      ],
      good_conditions: ['초반부터 정밀 기물이 붙을 때', '공격 속도 아이템이 준비됐을 때'],
      avoid_conditions: ['핵심 유닛이 심하게 겹칠 때'],
      fallback_plan: '핵심 유닛이 안 나오면 사이버시티 또는 라이트브링어 조합으로 피벗합니다.',
      rationale:
        '각 라운드 목표가 명확해 초보자도 운영 순서를 따라가기 쉽습니다.',
    },
  ],
  sources: [
    {
      title: '14.9 정밀 리롤 운영 가이드',
      url: 'https://example.com/tft/precision-reroll-guide',
      published_at: '2026-05-04T03:00:00Z',
      snippet: '정밀 리롤은 중반 안정화와 후반 보조 시너지 추가가 핵심입니다.',
      source_kind: 'community_post',
    },
  ],
  confidence: 'medium',
  warnings: [],
  generated_at: '2026-05-07T09:00:00Z',
};

export const mockItemPivotResponse: RecommendationResponse = {
  request_id: 'mock-item-pivot-001',
  patch_version: '14.9',
  intent: 'item_pivot',
  meta_summary:
    '초반에 곡궁이 많이 나온 경우 공격 속도 기반 캐리 덱을 우선 고려할 수 있습니다. 다만 핵심 유닛이 겹치면 같은 아이템을 활용하는 다른 물리 딜러 조합으로 빠르게 전환하는 편이 안전합니다.',
  decks: [
    {
      name: '정밀 곡궁 스타트',
      difficulty: 'medium',
      core_units: ['정밀의 사도', '기계 학자', '광신도', '강철의 수호자'],
      key_items: ['곡궁', '구인수의 격노검', '거인 학살자'],
      augment_direction: '공격 속도, 물리 딜러 강화, 전투 지속력 계열',
      playbook: [
        {
          phase: 'early',
          instruction: '곡궁은 바로 소모하지 말고 구인수 각을 보며 강한 임시 딜러에게 줍니다.',
        },
        {
          phase: 'mid',
          instruction: '정밀 기물이 붙으면 정밀 리롤로, 안 붙으면 물리 딜러 조합으로 갑니다.',
        },
        {
          phase: 'late',
          instruction: '후반에는 방어 아이템을 전열에 몰아주고 캐리 생존 시간을 늘립니다.',
        },
      ],
      good_conditions: ['초반 곡궁이 2개 이상일 때', '정밀 기물이 자연스럽게 붙을 때'],
      avoid_conditions: ['주문력 아이템 위주로 풀렸을 때'],
      fallback_plan: '정밀 각이 안 보이면 사이버시티 물리 딜러 조합으로 전환합니다.',
      rationale:
        '곡궁 기반 아이템을 자연스럽게 활용할 수 있어 초반 아이템 손실이 적습니다.',
    },
  ],
  sources: [
    {
      title: '14.9 아이템 스타트별 추천 방향',
      url: 'https://example.com/tft/14-9-item-openers',
      published_at: '2026-05-04T03:00:00Z',
      snippet: '곡궁 스타트는 공격 속도 기반 캐리 조합과 잘 맞습니다.',
      source_kind: 'meta_site',
    },
  ],
  confidence: 'medium',
  warnings: [],
  generated_at: '2026-05-07T09:00:00Z',
};
