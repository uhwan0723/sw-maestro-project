import { useState } from 'react';
import type { Agent, AgentOpinion } from '@/types';
import { SectionTitle } from '@/components/common';
import { UserInputBanner } from './UserInputBanner';
import { OpinionGrid } from './OpinionGrid';
import { RoundGuidePanel } from './RoundGuidePanel';
import { Button } from '@/components/ui/button';
import { Info, X } from 'lucide-react';
import { consultationContent } from '@/content';

interface OpinionPhaseProps {
  userInput: string;
  agents: Agent[];
  opinions: AgentOpinion[];
  onEditInput?: () => void;
}

export function OpinionPhase({ userInput, agents, opinions, onEditInput }: OpinionPhaseProps) {
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <UserInputBanner userInput={userInput} onEdit={onEditInput} />
      <SectionTitle
        title={consultationContent.round1.title}
        subtitle={consultationContent.round1.description}
        action={
          <Button
            variant={isGuideOpen ? 'secondary' : 'outline'}
            size="sm"
            className="gap-1.5 text-xs"
            aria-expanded={isGuideOpen}
            onClick={() => setIsGuideOpen((open) => !open)}
          >
            {isGuideOpen ? '안내 닫기' : '라운드 안내'}
            {isGuideOpen ? <X className="size-3.5" /> : <Info className="size-3.5" />}
          </Button>
        }
      />
      {isGuideOpen && <RoundGuidePanel round="round1" />}
      <OpinionGrid agents={agents} opinions={opinions} />
    </div>
  );
}
