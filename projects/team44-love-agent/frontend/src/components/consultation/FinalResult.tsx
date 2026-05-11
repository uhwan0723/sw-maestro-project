// 최종 결과 섹션 — 상황 정리, 에이전트 입장 분포, 조언, 타임라인 액션, 주의사항
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Agent, AgentOpinion, FinalResult as FinalResultType, StanceType } from '@/types';
import { resultContent } from '@/content';
import { AgentAvatar } from '@/components/agents/AgentAvatar';

interface FinalResultProps {
  result: FinalResultType;
  agents?: Agent[];
  opinions?: AgentOpinion[];
}

const STANCE_META: Record<StanceType, { label: string; bg: string; text: string }> = {
  proceed:  { label: '진행 권유', bg: 'bg-emerald-100',  text: 'text-emerald-700' },
  pause:    { label: '잠시 보류', bg: 'bg-amber-100',    text: 'text-amber-700'   },
  withdraw: { label: '신중 권고', bg: 'bg-slate-100',    text: 'text-slate-600'   },
  clarify:  { label: '확인 먼저', bg: 'bg-blue-100',     text: 'text-blue-700'    },
  mixed:    { label: '복합 의견', bg: 'bg-purple-100',   text: 'text-purple-700'  },
};

const TIMING_META = {
  immediate:  { label: '즉시',  step: 1, color: 'bg-primary', border: 'border-primary',        text: 'text-primary'        },
  short_term: { label: '단기',  step: 2, color: 'bg-amber-500', border: 'border-amber-500',    text: 'text-amber-600'      },
  long_term:  { label: '장기',  step: 3, color: 'bg-slate-400', border: 'border-slate-400',    text: 'text-slate-500'      },
} as const;

export function FinalResult({ result, agents, opinions }: FinalResultProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* 상황 정리 */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-2">
          <CardTitle className="text-sm font-semibold">{resultContent.situationTitle}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-sm text-muted-foreground">{result.situationSummary}</p>
        </CardContent>
      </Card>

      {/* 에이전트 입장 분포 */}
      {agents && opinions && opinions.length > 0 && (
        <Card className="p-4">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="text-sm font-semibold">에이전트 입장 분포</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="flex flex-wrap gap-3">
              {opinions.map((op) => {
                const agent = agents.find((a) => a.id === op.agentId);
                if (!agent) return null;
                const stance = STANCE_META[op.stance] ?? STANCE_META.mixed;
                return (
                  <div key={op.agentId} className="flex flex-col items-center gap-1.5">
                    <AgentAvatar agentId={agent.id} name={agent.name} colorKey={agent.colorKey} size="md" />
                    <span className="text-[11px] font-medium text-foreground">{agent.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${stance.bg} ${stance.text}`}>
                      {stance.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 최종 조언 */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-base font-semibold">{resultContent.adviceTitle}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-sm leading-7 whitespace-pre-wrap">{result.advice}</p>
        </CardContent>
      </Card>

      {/* 액션 아이템 타임라인 */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-4">
          <CardTitle className="text-sm font-semibold">{resultContent.actionItemsTitle}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="flex flex-col gap-0">
            {result.actionItems.map((item, i) => {
              const meta = TIMING_META[item.timing];
              const isLast = i === result.actionItems.length - 1;
              return (
                <div key={i} className="flex gap-4">
                  {/* 타임라인 스테퍼 */}
                  <div className="flex flex-col items-center">
                    <div className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${meta.color}`}>
                      {meta.step}
                    </div>
                    {!isLast && <div className="w-px flex-1 bg-border" style={{ minHeight: '1.5rem' }} />}
                  </div>
                  {/* 콘텐츠 */}
                  <div className={`flex flex-col gap-1 pb-5 ${isLast ? '' : ''}`}>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${meta.border} ${meta.text}`}>
                        {meta.label}
                      </span>
                      <span className="text-sm font-semibold">{item.title}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{item.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 기억하면 좋은 점 */}
      {result.caveats && result.caveats.length > 0 && (
        <Card className="p-4">
          <CardHeader className="p-0 pb-2">
            <CardTitle className="text-sm font-semibold">{resultContent.caveatsTitle}</CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex flex-col gap-1.5">
            {result.caveats.map((c, i) => (
              <p key={i} className="text-xs text-muted-foreground">• {c}</p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
