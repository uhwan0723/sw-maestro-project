'use client';

import { useState } from 'react';
import type { Agent, AgentOpinion, DiscussionMessage } from '@/types';
import { MESSAGE_TYPE_LABEL } from '@/types';
import { AgentAvatar } from './AgentAvatar';
import { Reply, ChevronDown, ChevronUp } from 'lucide-react';

interface AgentCardProps {
  agent: Agent;
  opinion?: AgentOpinion;
  message?: DiscussionMessage;
  agents?: Agent[];
  opinions?: AgentOpinion[];
}

export function AgentCard({ agent, opinion, message, agents, opinions }: AgentCardProps) {
  const [quoteOpen, setQuoteOpen] = useState(false);

  const content = opinion?.advice ?? message?.content;
  const messageType = message?.messageType;
  const label = messageType && messageType !== 'opinion' ? MESSAGE_TYPE_LABEL[messageType] : undefined;

  const replyTarget = message?.replyToAgentId && agents
    ? agents.find((a) => a.id === message.replyToAgentId)
    : undefined;
  const replyTargetOpinion = replyTarget && opinions
    ? opinions.find((o) => o.agentId === replyTarget.id)
    : undefined;

  return (
    <div
      className="flex h-full flex-col gap-3 rounded-xl p-4"
      style={{ backgroundColor: `color-mix(in oklch, var(--${agent.colorKey}) 10%, white)` }}
    >
      {/* 헤더 */}
      <div className="flex items-start gap-2.5">
        <AgentAvatar agentId={agent.id} name={agent.name} colorKey={agent.colorKey} size="md" />
        <div className="flex flex-1 flex-col gap-0.5 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-sm font-semibold leading-tight">{agent.name}</span>
            {label && (
              <span
                className="rounded-md px-2 py-0.5 text-[10px] font-semibold shrink-0"
                style={{
                  backgroundColor: `color-mix(in oklch, var(--${agent.colorKey}) 20%, white)`,
                  color: `var(--${agent.colorKey})`,
                }}
              >
                {label}
              </span>
            )}
          </div>
          <span className="text-xs text-muted-foreground truncate">{agent.persona}</span>
        </div>
      </div>

      {/* 반박 대상 배너 (클릭하면 원문 토글) */}
      {replyTarget && (
        <div className="flex flex-col gap-0">
          <button
            type="button"
            onClick={() => setQuoteOpen((v) => !v)}
            className="flex w-full items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-80"
            style={{
              backgroundColor: `color-mix(in oklch, var(--${replyTarget.colorKey}) 15%, white)`,
              color: `color-mix(in oklch, var(--${replyTarget.colorKey}) 80%, black)`,
              border: `1px solid color-mix(in oklch, var(--${replyTarget.colorKey}) 30%, white)`,
              borderRadius: quoteOpen ? '0.5rem 0.5rem 0 0' : '0.5rem',
            }}
          >
            <Reply className="size-3 shrink-0" />
            <AgentAvatar agentId={replyTarget.id} name={replyTarget.name} colorKey={replyTarget.colorKey} size="xs" />
            <span className="flex-1 text-left">
              <span className="font-semibold">{replyTarget.name}</span>의 의견에 반박
            </span>
            {replyTargetOpinion && (
              quoteOpen
                ? <ChevronUp className="size-3 shrink-0" />
                : <ChevronDown className="size-3 shrink-0" />
            )}
          </button>

          {/* 원문 인용 블록 */}
          {quoteOpen && replyTargetOpinion && (
            <div
              className="rounded-b-lg px-3 py-2.5 text-xs leading-relaxed text-muted-foreground"
              style={{
                backgroundColor: `color-mix(in oklch, var(--${replyTarget.colorKey}) 8%, white)`,
                borderLeft: `3px solid color-mix(in oklch, var(--${replyTarget.colorKey}) 50%, white)`,
                borderRight: `1px solid color-mix(in oklch, var(--${replyTarget.colorKey}) 30%, white)`,
                borderBottom: `1px solid color-mix(in oklch, var(--${replyTarget.colorKey}) 30%, white)`,
              }}
            >
              <p className="line-clamp-6 whitespace-pre-wrap">{replyTargetOpinion.advice}</p>
            </div>
          )}
        </div>
      )}

      {/* 본문 */}
      {content && <p className="flex-1 text-sm leading-relaxed">{content}</p>}
    </div>
  );
}
