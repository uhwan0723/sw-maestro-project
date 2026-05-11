import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { AgentCard } from '@/components/agents/AgentCard';
import { AGENTS } from '@/mocks/agents';
import { MOCK_CONSULTATION } from '@/mocks/consultation';

const meta: Meta<typeof AgentCard> = {
  title: 'Agents/AgentCard',
  component: AgentCard,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: `
에이전트 의견/토론 발언을 표시하는 카드입니다.

**단계별 라벨**
- 1단계 (opinion): 라벨 없음 — 초기 의견
- 2단계 (rebuttal): "반박 & 추가 의견" — 에이전트 고유 색
- 3단계 (deepdive): "심화 의견" — 에이전트 고유 색
        `,
      },
    },
  },
};
export default meta;

type Story = StoryObj<typeof AgentCard>;

export const 초기의견: Story = {
  parameters: { docs: { description: { story: '1단계 — 라벨 없음' } } },
  render: () => (
    <div className="grid grid-cols-3 gap-4 p-4">
      {MOCK_CONSULTATION.opinions.map((opinion) => {
        const agent = AGENTS.find((a) => a.id === opinion.agentId)!;
        return <AgentCard key={opinion.agentId} agent={agent} opinion={opinion} />;
      })}
    </div>
  ),
};

export const 반박추가의견: Story = {
  parameters: { docs: { description: { story: '2단계 — 에이전트 색 "반박 & 추가 의견" 라벨' } } },
  render: () => (
    <div className="grid grid-cols-3 gap-4 p-4">
      {MOCK_CONSULTATION.rounds[0].messages.map((message, i) => {
        const agent = AGENTS.find((a) => a.id === message.agentId)!;
        return <AgentCard key={i} agent={agent} message={{ ...message, messageType: 'rebuttal' }} />;
      })}
    </div>
  ),
};

export const 심화의견: Story = {
  parameters: { docs: { description: { story: '3단계 — 에이전트 색 "심화 의견" 라벨' } } },
  render: () => (
    <div className="grid grid-cols-3 gap-4 p-4">
      {MOCK_CONSULTATION.rounds[1].messages.map((message, i) => {
        const agent = AGENTS.find((a) => a.id === message.agentId)!;
        return <AgentCard key={i} agent={agent} message={{ ...message, messageType: 'deepdive' }} />;
      })}
    </div>
  ),
};
