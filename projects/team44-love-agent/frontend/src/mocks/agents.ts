import type { Agent } from '@/types';

export const AGENTS = [
  {
    id: 'realist',
    name: '현실주의자',
    persona: '행동과 결과 중심',
    tone: '직설적이고 현실적인 조언',
    colorKey: 'agent-realist',
  },
  {
    id: 'empath',
    name: '공감형 감성론자',
    persona: '감정 우선, 따뜻한 말투',
    tone: '따뜻하고 다정한 말투',
    colorKey: 'agent-empath',
  },
  {
    id: 'analyst',
    name: '신중한 분석가',
    persona: '맥락·패턴 분석, 차분',
    tone: '논리적이고 차분한 말투',
    colorKey: 'agent-analyst',
  },
  {
    id: 'actor',
    name: '행동파 조언자',
    persona: '행동 권유, 적극적',
    tone: '적극적이고 명확한 말투',
    colorKey: 'agent-actor',
  },
  {
    id: 'mediator',
    name: '균형형 중재자',
    persona: '양측 고려, 중립적',
    tone: '중립적이고 부드러운 말투',
    colorKey: 'agent-mediator',
  },
  {
    id: 'friend',
    name: '친구형 상담자',
    persona: '캐주얼, 친근한 말투',
    tone: '친근하고 편한 말투',
    colorKey: 'agent-friend',
  },
] as const satisfies Agent[];
