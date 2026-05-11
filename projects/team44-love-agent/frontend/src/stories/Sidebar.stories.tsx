import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { Sidebar } from '@/components/layout/Sidebar';
import { AGENTS } from '@/mocks/agents';

const meta: Meta<typeof Sidebar> = {
  title: 'Layout/Sidebar',
  component: Sidebar,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: `
좌측 고정 사이드바입니다.

**구성**
- 상단: 앱 로고 + 타이틀
- 네비게이션: 새로운 상담 / 상담 히스토리 / 사용 방법
- 에이전트 목록: 이니셜 아바타 + 이름 + 페르소나 요약
- 하단: AI 안내 문구

**로고 교체**
\`public/logo.svg\` 파일을 추가하면 자동으로 반영됩니다.
        `,
      },
    },
    layout: 'fullscreen',
  },
};
export default meta;

type Story = StoryObj<typeof Sidebar>;

export const Default: Story = {
  render: () => (
    <div className="flex h-screen">
      <Sidebar agents={[...AGENTS]} />
      <div className="flex-1 bg-muted/30" />
    </div>
  ),
};
