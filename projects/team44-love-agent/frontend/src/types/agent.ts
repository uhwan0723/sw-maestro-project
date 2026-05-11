// 에이전트 식별자 및 기본 타입 정의
export type AgentId =
  | 'realist'
  | 'empath'
  | 'analyst'
  | 'actor'
  | 'mediator'
  | 'friend';

export interface Agent {
  id: AgentId;
  name: string;
  persona: string;
  tone: string;
  colorKey: string;
}
