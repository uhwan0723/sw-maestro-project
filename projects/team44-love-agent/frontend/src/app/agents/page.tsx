'use client';

import { Sidebar } from '@/components/layout';
import { AgentAvatar } from '@/components/agents';
import { AGENTS } from '@/mocks/agents';

export default function AgentsPage() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar agents={AGENTS} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="shrink-0 px-10 pb-2 pt-8">
          <h1 className="text-2xl font-bold">에이전트 소개</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            상담에 참여하는 6명의 에이전트가 어떤 관점으로 말하는지 확인합니다.
          </p>
        </header>

        <div className="flex-1 overflow-y-auto px-10 py-4">
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {AGENTS.map((agent) => (
              <article key={agent.id} className="rounded-2xl border bg-white p-5 shadow-sm">
                <div className="flex items-center gap-3">
                  <AgentAvatar agentId={agent.id} name={agent.name} colorKey={agent.colorKey} size="md" />
                  <div className="min-w-0">
                    <h2 className="truncate text-base font-semibold">{agent.name}</h2>
                    <p className="mt-0.5 text-xs text-muted-foreground">{agent.persona}</p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{agent.tone}</p>
              </article>
            ))}
          </section>
        </div>
      </main>
    </div>
  );
}
