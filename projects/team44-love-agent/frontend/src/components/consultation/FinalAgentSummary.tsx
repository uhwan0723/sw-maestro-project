// 최종 결과 하단 — 참여 에이전트 목록 + 결과 저장 버튼 + footer 안내
import { Button } from '@/components/ui/button';
import { AgentAvatar } from '@/components/agents';
import type { Agent } from '@/types';
import { resultContent } from '@/content';

interface FinalAgentSummaryProps {
  agents: Agent[];
  onSave?: () => void;
}

export function FinalAgentSummary({ agents, onSave }: FinalAgentSummaryProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* 참여 에이전트 */}
      <div className="flex items-center justify-between rounded-xl border bg-white p-4">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold text-muted-foreground">
            {resultContent.contributingAgentsTitle}
          </span>
          <div className="flex items-center gap-2">
            {agents.map((agent) => (
              <AgentAvatar
                key={agent.id}
                agentId={agent.id}
                name={agent.name}
                colorKey={agent.colorKey}
                size="sm"
              />
            ))}
          </div>
        </div>
        <Button size="sm" onClick={onSave}>
          {resultContent.saveButton}
        </Button>
      </div>

      {/* footer 안내 */}
      <p className="text-xs leading-relaxed text-muted-foreground text-center px-2">
        {resultContent.footerNote}
      </p>
    </div>
  );
}
