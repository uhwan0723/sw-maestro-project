'use client';

// 우측 패널 — 다음 단계 버튼, 라운드 목표, 팁
import { Button } from '@/components/ui/button';
import { ChevronRight, Lightbulb } from 'lucide-react';
import type { AgentOpinion, Agent, ConsultationStep } from '@/types';
import { consultationContent } from '@/content';

const ROUND_TIPS = [
  '모든 의견을 열린 마음으로 살펴보세요.',
  '다양한 관점이 확신의 결론을 만듭니다.',
  '다음 라운드로 넘어가도 이전 내용은 계속 확인할 수 있어요.',
];

interface RoundSummaryPanelProps {
  agents: Agent[];
  opinions: AgentOpinion[];
  onNext: () => void;
  isLastRound: boolean;
  canGoNext: boolean;
  currentRound: number;
  step: ConsultationStep;
}

export function RoundSummaryPanel({ onNext, isLastRound, canGoNext, step }: RoundSummaryPanelProps) {
  const roundInfo = step === 'opinions' ? consultationContent.round1 : consultationContent.round2;
  const nextLabel = getNextLabel(step, isLastRound, canGoNext);

  return (
    <div className="flex flex-col gap-3">
      <Button onClick={onNext} disabled={!canGoNext} className="w-full gap-1.5">
        {nextLabel}
        <ChevronRight className="size-4" />
      </Button>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <p className="mb-2 text-xs font-semibold text-muted-foreground">이번 라운드 목표</p>
        <p className="text-xs leading-relaxed text-foreground">{roundInfo.description}</p>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="mb-2 flex items-center gap-1.5">
          <Lightbulb className="size-3.5 text-primary" />
          <p className="text-xs font-semibold text-muted-foreground">팁</p>
        </div>
        <ul className="flex flex-col gap-1.5">
          {ROUND_TIPS.map((tip, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <span className="mt-0.5 text-primary">•</span>
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function getNextLabel(step: ConsultationStep, isLastRound: boolean, canGoNext: boolean) {
  if (!canGoNext) return '다음 단계 준비 중';
  if (isLastRound) return '최종 결과 보기';
  if (step === 'opinions') return '2라운드 보기';
  return '다음 단계로 이동';
}
