'use client';

import { useRouter } from 'next/navigation';
import { Clock3, FileText, History, MessageSquareText, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sidebar } from '@/components/layout';
import { useConsultationStore } from '@/stores/consultationStore';
import { AGENTS } from '@/mocks/agents';

export default function HistoryPage() {
  const router = useRouter();
  const { consultationId, backendStatus, session, reset } = useConsultationStore();

  function handleNewConsultation() {
    reset();
    router.push('/');
  }

  function handleOpenCurrent() {
    if (consultationId) {
      router.push(`/consultation/${consultationId}`);
    }
  }

  const totalMessages = session
    ? session.opinions.length + session.rounds.reduce((sum, round) => sum + round.messages.length, 0)
    : 0;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar agents={AGENTS} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="flex shrink-0 items-start justify-between px-10 pb-2 pt-8">
          <div>
            <h1 className="text-2xl font-bold">상담 기록</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              현재 로컬 세션에서 진행 중인 상담 상태를 확인합니다.
            </p>
          </div>
          <Button variant="outline" size="sm" className="shrink-0 gap-1.5" onClick={handleNewConsultation}>
            <RotateCcw className="size-3.5" />
            새 상담 시작
          </Button>
        </header>

        <div className="flex flex-1 overflow-y-auto px-10 py-4">
          {!consultationId || !session ? (
            <section className="flex w-full flex-col items-center justify-center rounded-2xl border bg-white p-8 text-center shadow-sm">
              <History className="size-10 text-muted-foreground" />
              <h2 className="mt-4 text-lg font-semibold">아직 표시할 상담 기록이 없습니다</h2>
              <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
                현재 통합본은 DB 저장 없이 로컬 FastAPI 메모리 저장소로 실행됩니다. 상담을 시작하면 이 화면에서
                현재 상담 상태를 볼 수 있습니다.
              </p>
              <Button className="mt-5" onClick={handleNewConsultation}>
                상담 시작하기
              </Button>
            </section>
          ) : (
            <section className="grid w-full gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
              <article className="rounded-2xl border bg-white p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <Clock3 className="size-5 text-muted-foreground" />
                  <h2 className="text-lg font-semibold">현재 상담</h2>
                </div>
                <div className="mt-4 rounded-xl bg-muted p-4">
                  <p className="text-xs font-medium text-muted-foreground">고민 내용</p>
                  <p className="mt-2 max-h-32 overflow-y-auto text-sm leading-relaxed text-foreground">
                    {session.userInput}
                  </p>
                </div>
                <Button className="mt-5" onClick={handleOpenCurrent}>
                  현재 상담 열기
                </Button>
              </article>

              <aside className="rounded-2xl border bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold">진행 상태</p>
                <div className="mt-4 space-y-3">
                  <Metric label="상태" value={getStatusLabel(backendStatus)} icon={Clock3} />
                  <Metric label="1차 의견" value={`${session.opinions.length}개`} icon={MessageSquareText} />
                  <Metric label="토론 메시지" value={`${totalMessages}개`} icon={MessageSquareText} />
                  <Metric label="최종 결과" value={session.finalResult ? '완료' : '진행 중'} icon={FileText} />
                </div>
              </aside>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Clock3;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl bg-muted px-3 py-3">
      <div className="flex min-w-0 items-center gap-2">
        <Icon className="size-4 shrink-0 text-muted-foreground" />
        <span className="truncate text-xs text-muted-foreground">{label}</span>
      </div>
      <span className="shrink-0 text-sm font-semibold text-foreground">{value}</span>
    </div>
  );
}

function getStatusLabel(status: string | null) {
  if (status === 'completed') return '완료';
  if (status === 'failed') return '실패';
  if (status === 'terminated') return '중단';
  if (status === 'running') return '진행 중';
  if (status === 'pending') return '대기 중';
  return '준비 중';
}
