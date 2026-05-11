import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { AgentAvatar } from '@/components/agents/AgentAvatar';
import { AGENTS } from '@/mocks/agents';

const meta: Meta<typeof AgentAvatar> = {
  title: 'Agents/AgentAvatar',
  component: AgentAvatar,
  tags: ['autodocs'],
};
export default meta;

type Story = StoryObj<typeof AgentAvatar>;

export const AllAgents: Story = {
  render: () => (
    <div className="flex gap-4 p-4">
      {AGENTS.map((agent) => (
        <div key={agent.id} className="flex flex-col items-center gap-2">
          <AgentAvatar agentId={agent.id} name={agent.name} colorKey={agent.colorKey} />
          <span className="text-xs">{agent.name}</span>
        </div>
      ))}
    </div>
  ),
};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-end gap-4 p-4">
      {(['sm', 'md', 'lg'] as const).map((size) => (
        <div key={size} className="flex flex-col items-center gap-2">
          <AgentAvatar
            agentId={AGENTS[0].id}
            name={AGENTS[0].name}
            colorKey={AGENTS[0].colorKey}
            size={size}
          />
          <span className="text-xs">{size}</span>
        </div>
      ))}
    </div>
  ),
};
