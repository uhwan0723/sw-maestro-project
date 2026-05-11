import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { LoadingCard } from '@/components/status/LoadingCard';
import { LoadingOverlay } from '@/components/status/LoadingOverlay';

const meta: Meta = {
  title: 'Status/Loading',
  tags: ['autodocs'],
};
export default meta;

export const Card: StoryObj = {
  render: () => (
    <div className="grid grid-cols-3 gap-4 p-4">
      <LoadingCard />
      <LoadingCard />
      <LoadingCard />
    </div>
  ),
};

export const Overlay: StoryObj = {
  render: () => <LoadingOverlay phase="analyzing" />,
};

export const OverlayGenerating: StoryObj = {
  render: () => <LoadingOverlay phase="generatingOpinions" />,
};
