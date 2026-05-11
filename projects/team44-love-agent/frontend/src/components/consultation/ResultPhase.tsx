import type { Agent, AgentOpinion, FinalResult as FinalResultType } from '@/types';
import { SectionTitle } from '@/components/common';
import { FinalResult } from './FinalResult';
import { FinalAgentSummary } from './FinalAgentSummary';
import { resultContent } from '@/content';

interface ResultPhaseProps {
  agents: Agent[];
  opinions: AgentOpinion[];
  result: FinalResultType;
  onSave?: () => void;
}

export function ResultPhase({ agents, opinions, result, onSave }: ResultPhaseProps) {
  return (
    <div className="flex flex-col gap-6">
      <SectionTitle title={resultContent.title || '최종 결과'} />
      <FinalResult result={result} agents={agents} opinions={opinions} />
      <FinalAgentSummary agents={agents} onSave={onSave} />
    </div>
  );
}
