'use client';

// 우측 패널 — 단계에 따라 다른 패널 렌더링
import { motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import { RoundSummaryPanel } from './RoundSummaryPanel';
import type { AgentOpinion, Agent, ConsultationStep } from '@/types';

const PROGRESS_STEPS = [
  { label: '1라운드', sub: '에이전트 의견 수집' },
  { label: '2라운드', sub: '반박 및 재논의' },
  { label: '3라운드', sub: '심화 논의' },
  { label: '최종 리포트', sub: '종합 리포트 제공' },
];

interface RightPanelProps {
  step: ConsultationStep;
  agents: Agent[];
  opinions: AgentOpinion[];
  isLastRound: boolean;
  canGoNext: boolean;
  currentRound: number;
  onNext: () => void;
}

export function RightPanel({ step, agents, opinions, isLastRound, canGoNext, currentRound, onNext }: RightPanelProps) {
  if (step === 'discussion' || step === 'opinions') {
    return (
      <RoundSummaryPanel
        agents={agents}
        opinions={opinions}
        onNext={onNext}
        isLastRound={isLastRound}
        canGoNext={canGoNext}
        currentRound={currentRound}
        step={step}
      />
    );
  }

  if (step === 'result') {
    return (
      <motion.div
        className="flex flex-col gap-3"
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
      >
        {/* 완료 뱃지 */}
        <div className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 shadow-sm">
          <CheckCircle2 className="size-4 text-primary" />
          <span className="text-sm font-semibold">상담 완료</span>
        </div>

        {/* 진행 현황 */}
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <p className="mb-3 text-xs font-semibold text-muted-foreground">진행 현황</p>
          <ul className="flex flex-col gap-3">
            {PROGRESS_STEPS.map((s, i) => (
              <motion.li
                key={i}
                className="flex items-start gap-2"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08, duration: 0.25 }}
              >
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" />
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-foreground">{s.label}</span>
                  <span className="text-[11px] text-muted-foreground">{s.sub} 완료</span>
                </div>
              </motion.li>
            ))}
          </ul>
        </div>

        {/* 안내 */}
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <p className="text-xs leading-relaxed text-muted-foreground">
            AI 에이전트의 의견은 참고용입니다. 최종 판단은 본인이 하세요.
          </p>
        </div>
      </motion.div>
    );
  }

  return null;
}
