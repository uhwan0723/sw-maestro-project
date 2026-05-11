import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { StepBar } from '@/components/layout/StepBar';

const meta: Meta<typeof StepBar> = {
  title: 'Layout/StepBar',
  component: StepBar,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: `
상담 진행 단계를 상단에 표시하는 스텝 바입니다.

**5단계 구성**
1. 고민 입력
2. 의견 분석
3. 1라운드 토론
4. 2라운드 토론
5. 최종 결과

**상태 표시**
- 완료 단계: 보라색 원 + 체크(✓)
- 현재 단계: 보라색 pill 강조
- 미완료 단계: 회색 원
        `,
      },
    },
  },
};
export default meta;

type Story = StoryObj<typeof StepBar>;

export const 고민입력: Story = { args: { step: 'input', currentRound: 1 } };
export const 의견분석: Story = { args: { step: 'opinions', currentRound: 1 } };
export const 라운드1: Story = { args: { step: 'discussion', currentRound: 1 } };
export const 라운드2: Story = { args: { step: 'discussion', currentRound: 2 } };
export const 최종결과: Story = { args: { step: 'result', currentRound: 2 } };

export const 전체단계: Story = {
  parameters: {
    docs: {
      description: {
        story: '5단계 전체를 한눈에 비교할 수 있습니다.',
      },
    },
  },
  render: () => (
    <div className="flex flex-col gap-6 p-4">
      {[
        { step: 'input' as const, currentRound: 1, label: '1단계 — 고민 입력' },
        { step: 'opinions' as const, currentRound: 1, label: '2단계 — 의견 분석' },
        { step: 'discussion' as const, currentRound: 1, label: '3단계 — 1라운드' },
        { step: 'discussion' as const, currentRound: 2, label: '4단계 — 2라운드' },
        { step: 'result' as const, currentRound: 2, label: '5단계 — 최종 결과' },
      ].map(({ step, currentRound, label }) => (
        <div key={label} className="flex items-center gap-4">
          <span className="w-28 shrink-0 text-xs text-muted-foreground">{label}</span>
          <StepBar step={step} currentRound={currentRound} />
        </div>
      ))}
    </div>
  ),
};
