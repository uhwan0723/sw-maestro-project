import { motion } from 'framer-motion';
import type { Agent, AgentOpinion, DiscussionRound as DiscussionRoundType } from '@/types';
import { AgentCard } from '@/components/agents';

interface DiscussionRoundProps {
  round: DiscussionRoundType;
  agents: Agent[];
  opinions: AgentOpinion[];
}

export function DiscussionRound({ round, agents, opinions }: DiscussionRoundProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {round.messages.map((message, i) => {
        const agent = agents.find((a) => a.id === message.agentId);
        if (!agent) return null;
        return (
          <motion.div
            key={i}
            className="h-full"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.3, ease: 'easeOut' }}
          >
            <AgentCard agent={agent} message={message} agents={agents} opinions={opinions} />
          </motion.div>
        );
      })}
    </div>
  );
}
