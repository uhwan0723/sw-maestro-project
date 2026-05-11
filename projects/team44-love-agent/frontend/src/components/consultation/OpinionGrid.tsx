import { motion } from 'framer-motion';
import { AgentCard } from '@/components/agents';
import type { Agent, AgentOpinion } from '@/types';

interface OpinionGridProps {
  agents: Agent[];
  opinions: AgentOpinion[];
}

export function OpinionGrid({ agents, opinions }: OpinionGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {opinions.map((opinion, i) => {
        const agent = agents.find((a) => a.id === opinion.agentId);
        if (!agent) return null;
        return (
          <motion.div
            key={opinion.agentId}
            className="h-full"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.3, ease: 'easeOut' }}
          >
            <AgentCard agent={agent} opinion={opinion} />
          </motion.div>
        );
      })}
    </div>
  );
}
