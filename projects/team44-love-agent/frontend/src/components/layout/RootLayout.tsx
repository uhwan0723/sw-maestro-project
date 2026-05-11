// 전체 레이아웃 — 사이드바, StepBar, 메인, 우측 패널
import type { ReactNode } from 'react';
import type { Agent, AgentOpinion, ConsultationStep } from '@/types';
import { Sidebar } from './Sidebar';
import { StepBar } from './StepBar';
import { RightPanel } from './RightPanel';

interface RootLayoutProps {
  children: ReactNode;
  agents: Agent[];
  step: ConsultationStep;
  currentRound: number;
  opinions: AgentOpinion[];
  isLastRound: boolean;
  canGoNext: boolean;
  onNext: () => void;
  showSidebar?: boolean;
  showRightPanel?: boolean;
}

export function RootLayout({
  children,
  agents,
  step,
  currentRound,
  opinions,
  isLastRound,
  canGoNext,
  onNext,
  showSidebar = true,
  showRightPanel = true,
}: RootLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      {showSidebar && <Sidebar agents={agents} />}
      <div className="flex flex-1 flex-col overflow-hidden px-6 py-4 gap-4">
        {/* StepBar 상단 */}
        <div className="flex justify-center rounded-2xl bg-white px-6 py-3 shadow-sm shrink-0">
          <StepBar step={step} currentRound={currentRound} />
        </div>

        {/* 메인 + 우측 패널 */}
        <div className="flex flex-1 gap-4 overflow-hidden">
          <div className="flex-1 overflow-y-auto rounded-2xl bg-white p-6 shadow-sm">
            {children}
          </div>

          {showRightPanel && (
            <div className="w-64 shrink-0 overflow-y-auto">
              <RightPanel
                step={step}
                agents={agents}
                opinions={opinions}
                isLastRound={isLastRound}
                canGoNext={canGoNext}
                currentRound={currentRound}
                onNext={onNext}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
