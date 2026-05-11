import { CheckCircle2, Flag, ListChecks } from 'lucide-react';

type RoundGuideType = 'round1' | 'round2' | 'round3';

const ROUND_GUIDES: Record<RoundGuideType, {
  title: string;
  goal: string;
  checks: string[];
  next: string;
}> = {
  round1: {
    title: '1라운드 안내',
    goal: '각 에이전트가 같은 고민을 서로 다른 관점에서 먼저 해석합니다.',
    checks: [
      '어떤 관점이 내 상황과 가장 가까운지 비교해보세요.',
      '서로 다른 조언이 나오는 이유를 함께 살펴보세요.',
      '아직 결론이 아니라 초안 의견이라는 점을 기억하세요.',
    ],
    next: '6명의 첫 의견이 모두 모이면 2라운드 토론으로 넘어갈 수 있습니다.',
  },
  round2: {
    title: '2라운드 안내',
    goal: '에이전트들이 서로의 의견을 비교하고, 빠진 지점이나 위험한 단정을 보완합니다.',
    checks: [
      '누가 어떤 의견에 동의하거나 반박하는지 확인해보세요.',
      '처음 의견보다 더 현실적인 행동 방향이 나오는지 살펴보세요.',
      '한쪽 관점에만 치우치지 않는지 비교해보세요.',
    ],
    next: '토론이 정리되면 3라운드에서 각 에이전트의 마지막 입장을 확인합니다.',
  },
  round3: {
    title: '3라운드 안내',
    goal: '앞선 토론을 반영해 각 에이전트가 최종 입장을 정리합니다.',
    checks: [
      '처음 의견과 최종 입장이 달라졌는지 확인해보세요.',
      '공통으로 강조되는 조언이 무엇인지 찾아보세요.',
      '최종 리포트에 들어갈 핵심 결론을 미리 살펴보세요.',
    ],
    next: '마지막 입장까지 확인한 뒤 최종 조언 리포트로 넘어갑니다.',
  },
};

interface RoundGuidePanelProps {
  round: RoundGuideType;
}

export function RoundGuidePanel({ round }: RoundGuidePanelProps) {
  const guide = ROUND_GUIDES[round];

  return (
    <aside className="rounded-2xl border bg-muted/40 p-4">
      <div className="flex items-start gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Flag className="size-4 text-primary" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">{guide.title}</p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{guide.goal}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="rounded-xl bg-white p-3">
          <div className="mb-2 flex items-center gap-2">
            <ListChecks className="size-4 text-primary" />
            <p className="text-xs font-semibold text-muted-foreground">확인할 점</p>
          </div>
          <ul className="space-y-2">
            {guide.checks.map((check) => (
              <li key={check} className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
                <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-primary" />
                <span>{check}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl bg-white p-3">
          <p className="text-xs font-semibold text-muted-foreground">다음 단계</p>
          <p className="mt-2 text-xs leading-relaxed text-foreground">{guide.next}</p>
        </div>
      </div>
    </aside>
  );
}
