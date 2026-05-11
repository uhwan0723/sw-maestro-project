import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { RoundSummaryPanel } from '@/components/layout/RoundSummaryPanel';
import { AGENTS } from '@/mocks/agents';
import { MOCK_CONSULTATION } from '@/mocks/consultation';

const meta: Meta<typeof RoundSummaryPanel> = {
  title: 'Layout/RoundSummaryPanel',
  component: RoundSummaryPanel,
  tags: ['autodocs'],
};
export default meta;

type Story = StoryObj<typeof RoundSummaryPanel>;

export const MidRound: Story = {
  args: {
    agents: [...AGENTS],
    opinions: MOCK_CONSULTATION.opinions,
    isLastRound: false,
    onNext: () => {},
  },
};

export const LastRound: Story = {
  args: {
    agents: [...AGENTS],
    opinions: MOCK_CONSULTATION.opinions,
    isLastRound: true,
    onNext: () => {},
  },
};
