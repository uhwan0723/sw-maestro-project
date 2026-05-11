'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useConsultationStore } from '@/stores/consultationStore';
import { AGENTS } from '@/mocks/agents';
import { RootLayout } from '@/components/layout';
import { OpinionPhase, DiscussionPhase, ResultPhase } from '@/components/consultation';
import { LoadingOverlay, ErrorMessage } from '@/components/status';

export default function ConsultationPage() {
  const params = useParams<{ sessionId: string }>();
  const {
    step,
    currentRound,
    session,
    backendStatus,
    errorMessage,
    consultationId,
    loadConsultation,
    goToNextRound,
  } = useConsultationStore();

  useEffect(() => {
    const sessionId = params.sessionId;
    if (sessionId && consultationId !== sessionId) {
      void loadConsultation(sessionId);
    }
  }, [consultationId, loadConsultation, params.sessionId]);

  if (step === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex w-full max-w-4xl flex-col gap-4 rounded-2xl bg-white p-8 shadow-sm">
          <LoadingOverlay phase={backendStatus ?? 'analyzing'} />
          {errorMessage && <ErrorMessage message={errorMessage} />}
        </div>
      </div>
    );
  }

  if (!session) {
    return <ErrorMessage message={errorMessage ?? '세션 정보를 찾을 수 없습니다.'} />;
  }

  const isLastRound = step === 'discussion' && currentRound >= session.rounds.length;
  const canGoNext = getCanGoNext(step, session, currentRound);

  function renderContent() {
    if (!session) return null;

    if (step === 'opinions') {
      return (
        <OpinionPhase
          userInput={session.userInput}
          agents={AGENTS}
          opinions={session.opinions}
        />
      );
    }

    if (step === 'discussion') {
      return (
        <DiscussionPhase
          userInput={session.userInput}
          agents={AGENTS}
          opinions={session.opinions}
          rounds={session.rounds}
          currentRound={currentRound}
        />
      );
    }

    if (step === 'result' && session.finalResult) {
      return <ResultPhase agents={AGENTS} opinions={session.opinions} result={session.finalResult} />;
    }

    return null;
  }

  return (
    <RootLayout
      agents={AGENTS}
      step={step}
      currentRound={currentRound}
      opinions={session.opinions}
      isLastRound={isLastRound}
      canGoNext={canGoNext}
      onNext={goToNextRound}
    >
      {renderContent()}
    </RootLayout>
  );
}

function getCanGoNext(
  step: ReturnType<typeof useConsultationStore.getState>['step'],
  session: NonNullable<ReturnType<typeof useConsultationStore.getState>['session']>,
  currentRound: number,
) {
  if (step === 'opinions') {
    return session.opinions.length >= AGENTS.length && (session.rounds.length > 0 || Boolean(session.finalResult));
  }

  if (step === 'discussion') {
    return currentRound < session.rounds.length || Boolean(session.finalResult);
  }

  return false;
}
