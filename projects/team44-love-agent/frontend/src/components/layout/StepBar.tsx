'use client';

// 상단 진행 단계 바 — 완료 단계 클릭 시 해당 step으로 이동
import { Check } from 'lucide-react';
import { motion } from 'framer-motion';
import type { ConsultationStep } from '@/types';
import { consultationContent } from '@/content';

const { steps } = consultationContent;

const STEPS: { title: string; subtitle: string; step: ConsultationStep; round?: number }[] = [
  { title: steps.analysis.title, subtitle: steps.analysis.subtitle, step: 'opinions' },
  { title: steps.round1.title, subtitle: steps.round1.subtitle, step: 'opinions' },
  { title: steps.round2.title, subtitle: steps.round2.subtitle, step: 'discussion', round: 1 },
  { title: steps.round3.title, subtitle: steps.round3.subtitle, step: 'discussion', round: 2 },
  { title: steps.result.title, subtitle: steps.result.subtitle, step: 'result' },
];

interface StepBarProps {
  step: ConsultationStep;
  currentRound: number;
  onStepClick?: (step: ConsultationStep, round?: number) => void;
}

function getActiveIndex(step: ConsultationStep, currentRound: number): number {
  if (step === 'input' || step === 'loading') return 0;
  if (step === 'opinions') return 1;
  if (step === 'discussion') return currentRound + 1;
  if (step === 'result') return 4;
  return 0;
}

export function StepBar({ step, currentRound, onStepClick }: StepBarProps) {
  const activeIndex = getActiveIndex(step, currentRound);

  return (
    <div className="flex items-center">
      {STEPS.map((s, i) => {
        const isDone = i < activeIndex;
        const isActive = i === activeIndex;
        const isClickable = isDone && !!onStepClick;

        return (
          <div key={i} className="flex items-center">
            <motion.div
              className={`flex items-center gap-2 ${isClickable ? 'cursor-pointer' : ''}`}
              onClick={() => isClickable && onStepClick?.(s.step, s.round)}
              whileHover={isClickable ? { scale: 1.03 } : {}}
              whileTap={isClickable ? { scale: 0.97 } : {}}
              transition={{ duration: 0.15 }}
            >
              <motion.span
                className={`flex shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                  isActive
                    ? 'size-8 bg-primary text-primary-foreground'
                    : isDone
                      ? 'size-8 bg-primary/20 text-primary'
                      : 'size-8 bg-muted text-muted-foreground'
                }`}
                animate={isActive ? { scale: [1, 1.08, 1] } : {}}
                transition={{ duration: 0.4, ease: 'easeOut' }}
              >
                {isDone ? <Check className="size-4" strokeWidth={2.5} /> : i + 1}
              </motion.span>
              <div className="flex flex-col">
                <span className={`text-sm font-semibold leading-tight ${
                  isActive ? 'text-foreground' : isDone ? 'text-primary/70' : 'text-muted-foreground'
                }`}>
                  {s.title}
                </span>
                <span className={`text-xs leading-tight ${
                  isActive ? 'text-muted-foreground' : isDone ? 'text-primary/50' : 'text-muted-foreground/50'
                }`}>
                  {s.subtitle}
                </span>
              </div>
            </motion.div>

            {i < STEPS.length - 1 && (
              <div className="mx-3 flex gap-0.5">
                {Array.from({ length: 5 }).map((_, j) => (
                  <motion.span
                    key={j}
                    className="h-px w-1.5 bg-border"
                    animate={{ opacity: isDone ? 1 : 0.4 }}
                    transition={{ delay: j * 0.05 }}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
