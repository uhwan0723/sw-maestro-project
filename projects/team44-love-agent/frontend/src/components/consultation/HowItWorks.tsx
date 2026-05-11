import { PenLine, MessageSquare, RefreshCw, FileText, ChevronRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

const STEPS: { icon: LucideIcon; label: string; description: string }[] = [
  {
    icon: PenLine,
    label: '질문 입력',
    description: '연애 고민을 입력하면\n여섯 AI가 함께 분석을 시작해요.',
  },
  {
    icon: MessageSquare,
    label: '1라운드 의견 수집',
    description: '각 에이전트가 다양한 관점의\n의견과 조언을 제시해요.',
  },
  {
    icon: RefreshCw,
    label: '라운드별 반박/심화',
    description: '의견을 주고받으며 더 깊이 있게\n분석하고, 관점을 넓혀가요.',
  },
  {
    icon: FileText,
    label: '최종 종합 리포트',
    description: '모든 논의를 종합해\n최적의 조언을 제공합니다.',
  },
];

export function HowItWorks() {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border bg-white p-6 shadow-sm">
      <div>
        <p className="font-semibold">상담 진행 과정</p>
        <p className="text-sm text-muted-foreground">
          여섯 AI 에이전트가 함께 단계적으로 고민을 분석하고 해결책을 찾아갑니다.
        </p>
      </div>
      <div className="flex items-start justify-center">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <div key={i} className="flex items-center">
              <div className="flex flex-col items-center gap-3 px-4 text-center">
                <div className="flex size-16 items-center justify-center rounded-full bg-primary/10">
                  <Icon className="size-7 text-primary" />
                </div>
                <p className="text-sm font-semibold">{step.label}</p>
                <p className="whitespace-pre-line text-xs text-muted-foreground">{step.description}</p>
              </div>
              {i < STEPS.length - 1 && (
                <ChevronRight className="mb-10 size-5 shrink-0 text-muted-foreground" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
