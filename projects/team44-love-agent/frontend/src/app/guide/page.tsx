'use client';

import { Database, Radio, Server, SquarePen } from 'lucide-react';
import { Sidebar } from '@/components/layout';
import { HowItWorks } from '@/components/consultation';
import { AGENTS } from '@/mocks/agents';

const LOCAL_NOTES = [
  {
    icon: Server,
    title: 'FastAPI 백엔드',
    description: '상담 생성과 결과 조회는 로컬 FastAPI 서버로 요청합니다.',
  },
  {
    icon: Radio,
    title: 'SSE 실시간 수신',
    description: '진행 중인 에이전트 의견과 완료 이벤트를 SSE로 받아 화면에 반영합니다.',
  },
  {
    icon: Database,
    title: 'DB 저장 없음',
    description: '현재 통합본은 로컬 메모리 저장 방식이라 서버 재시작 후 기록이 유지되지 않습니다.',
  },
];

export default function GuidePage() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar agents={AGENTS} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="shrink-0 px-10 pb-2 pt-8">
          <h1 className="text-2xl font-bold">사용 방법</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            로컬 실행 기준으로 상담이 어떤 순서로 진행되는지 확인합니다.
          </p>
        </header>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-10 py-4">
          <HowItWorks />

          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <SquarePen className="size-5 text-muted-foreground" />
              <h2 className="font-semibold">로컬 통합본 기준</h2>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-3">
              {LOCAL_NOTES.map((note) => {
                const Icon = note.icon;
                return (
                  <article key={note.title} className="rounded-xl bg-muted p-4">
                    <Icon className="size-5 text-muted-foreground" />
                    <h3 className="mt-3 text-sm font-semibold">{note.title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{note.description}</p>
                  </article>
                );
              })}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
