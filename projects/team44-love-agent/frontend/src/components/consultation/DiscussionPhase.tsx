import { useState } from 'react';
import type { Agent, AgentOpinion, DiscussionRound as DiscussionRoundType } from '@/types';
import { SectionTitle } from '@/components/common';
import { UserInputBanner } from './UserInputBanner';
import { DiscussionRound } from './DiscussionRound';
import { RoundGuidePanel } from './RoundGuidePanel';
import { Button } from '@/components/ui/button';
import { Info, X } from 'lucide-react';
import { consultationContent } from '@/content';

interface DiscussionPhaseProps {
  userInput: string;
  agents: Agent[];
  opinions: AgentOpinion[];
  rounds: DiscussionRoundType[];
  currentRound: number;
  onEditInput?: () => void;
}

export function DiscussionPhase({ userInput, agents, opinions, rounds, currentRound, onEditInput }: DiscussionPhaseProps) {
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const visibleRounds = rounds.filter((r) => r.roundNumber === currentRound);
  const guideRound = currentRound === 1 ? 'round2' : 'round3';

  return (
    <div className="flex flex-col gap-6">
      <UserInputBanner userInput={userInput} onEdit={onEditInput} />
      <SectionTitle
        title={`${currentRound + 1}라운드 - ${currentRound === 1 ? consultationContent.round2.title : consultationContent.round3.title}`}
        subtitle={currentRound === 1 ? consultationContent.round2.description : consultationContent.round3.description}
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
      {isGuideOpen && <RoundGuidePanel round={guideRound} />}
      <div className="flex flex-col gap-8">
        {visibleRounds.map((round) => (
          <DiscussionRound key={round.roundNumber} round={round} agents={agents} opinions={opinions} />
        ))}
      </div>
    </div>
  );
}
