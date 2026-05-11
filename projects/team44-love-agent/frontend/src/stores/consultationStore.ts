import { create } from 'zustand';
import type { ConsultationSession, ConsultationStep } from '@/types';
import {
  createConsultation,
  getConsultation,
  openConsultationEventSource,
  type BackendStreamEvent,
} from '@/lib/consultationApi';
import {
  isTerminalStatus,
  mapBackendMessage,
  mapBackendResponseToSession,
  mergeDiscussionMessage,
  mergeOpinion,
  type BackendConsultationResponse,
  type BackendStatus,
} from '@/lib/consultationMapper';

const EMPTY_SESSION: ConsultationSession = {
  userInput: '',
  opinions: [],
  rounds: [],
  finalResult: null,
};

type StoreState = Pick<ConsultationState, 'step' | 'currentRound' | 'session'>;

const INITIAL_STATE: StoreState = {
  step: 'input',
  currentRound: 1,
  session: null,
};

interface ConsultationState {
  step: ConsultationStep;
  currentRound: number;
  session: ConsultationSession | null;
  consultationId: string | null;
  backendStatus: BackendStatus | null;
  errorMessage: string | null;
  isSubmitting: boolean;
  eventSource: EventSource | null;

  setUserInput: (input: string) => void;
  startConsultation: () => Promise<string>;
  loadConsultation: (consultationId: string) => Promise<void>;
  setSession: (session: ConsultationSession) => void;
  goToNextRound: () => void;
  goToStep: (step: ConsultationStep, round?: number) => void;
  reset: () => void;
}

export const useConsultationStore = create<ConsultationState>((set, get) => ({
  ...INITIAL_STATE,
  consultationId: null,
  backendStatus: null,
  errorMessage: null,
  isSubmitting: false,
  eventSource: null,

  setUserInput: (input) => {
    set((state) => ({
      session: {
        ...(state.session ?? EMPTY_SESSION),
        userInput: input,
      },
    }));
  },

  startConsultation: async () => {
    if (process.env.NEXT_PUBLIC_USE_MOCK === 'true') {
      const { MOCK_CONSULTATION } = await import('@/mocks/consultation');
      set({
        step: 'opinions',
        session: MOCK_CONSULTATION,
        currentRound: 1,
        consultationId: 'mock',
        backendStatus: 'completed',
        errorMessage: null,
      });
      return 'mock';
    }

    const userInput = get().session?.userInput.trim();
    if (!userInput) {
      throw new Error('상담할 고민 내용을 먼저 입력해주세요.');
    }

    get().eventSource?.close();

    const consultationId = crypto.randomUUID();
    set({
      step: 'loading',
      currentRound: 1,
      consultationId,
      backendStatus: 'pending',
      errorMessage: null,
      isSubmitting: true,
      session: {
        ...EMPTY_SESSION,
        userInput,
      },
    });

    try {
      const started = await createConsultation(userInput, consultationId);
      set({ backendStatus: started.status, isSubmitting: false });
      attachEventSource(consultationId, set, get);
      return consultationId;
    } catch (error) {
      const message = error instanceof Error ? error.message : '상담 요청을 시작하지 못했어요.';
      set({ step: 'input', errorMessage: message, isSubmitting: false });
      throw error;
    }
  },

  loadConsultation: async (consultationId) => {
    if (process.env.NEXT_PUBLIC_USE_MOCK === 'true' || consultationId === 'mock') {
      const { MOCK_CONSULTATION } = await import('@/mocks/consultation');
      set({
        step: 'opinions',
        session: MOCK_CONSULTATION,
        currentRound: 1,
        consultationId: 'mock',
        backendStatus: 'completed',
        errorMessage: null,
      });
      return;
    }

    try {
      const shouldPreserveStep = get().consultationId === consultationId;
      const response = await getConsultation(consultationId);
      applyBackendResponse(response, set, get, { preserveStep: shouldPreserveStep });
      set({ consultationId, errorMessage: null });
      if (!isTerminalStatus(response.status)) {
        attachEventSource(consultationId, set, get);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '상담 정보를 불러오지 못했어요.';
      set({ errorMessage: message, step: 'loading' });
    }
  },

  setSession: (session) => {
    set({ session, step: 'opinions' });
  },

  goToNextRound: () => {
    const { step, session, currentRound } = get();
    if (!session) return;

    if (step === 'opinions') {
      if (session.rounds.length > 0) {
        set({ step: 'discussion', currentRound: 1 });
      } else if (session.finalResult) {
        set({ step: 'result' });
      }
    } else if (currentRound < session.rounds.length) {
      set({ currentRound: currentRound + 1 });
    } else if (session.finalResult) {
      set({ step: 'result' });
    }
  },

  goToStep: (step, round) => {
    set({ step, ...(round !== undefined ? { currentRound: round } : {}) });
  },

  reset: () => {
    get().eventSource?.close();
    set({
      ...INITIAL_STATE,
      consultationId: null,
      backendStatus: null,
      errorMessage: null,
      isSubmitting: false,
      eventSource: null,
    });
  },
}));

function attachEventSource(
  consultationId: string,
  set: typeof useConsultationStore.setState,
  get: typeof useConsultationStore.getState,
) {
  get().eventSource?.close();
  const eventSource = openConsultationEventSource(consultationId);
  set({ eventSource });

  const handleEvent = (event: MessageEvent<string>) => {
    const data = JSON.parse(event.data) as BackendStreamEvent;
    handleStreamEvent(data, set, get);
  };

  eventSource.addEventListener('status_changed', handleEvent);
  eventSource.addEventListener('agent_message_added', handleEvent);
  eventSource.addEventListener('completed', handleEvent);
  eventSource.addEventListener('error_occurred', handleEvent);
  eventSource.onerror = () => {
    if (!isTerminalStatus(get().backendStatus ?? 'pending')) {
      set({ errorMessage: '실시간 상담 연결이 잠시 끊겼어요. 결과 조회를 다시 시도해주세요.' });
    }
  };
}

function handleStreamEvent(
  event: BackendStreamEvent,
  set: typeof useConsultationStore.setState,
  get: typeof useConsultationStore.getState,
) {
  if (event.event_type === 'status_changed') {
    const status = event.payload.status as BackendStatus;
    set((state) => ({
      backendStatus: status,
      step: getStepAfterStatusUpdate(status, state.session, state.step),
    }));
    return;
  }

  if (event.event_type === 'agent_message_added') {
    const round = event.payload.round as 'round_1' | 'round_2' | 'round_3';
    const message = mapBackendMessage(round, event.payload.message as never);
    if (!message) return;

    set((state) => {
      const session = state.session ?? EMPTY_SESSION;
      if (round === 'round_1' && 'advice' in message) {
        const next = mergeOpinion(session, message);
        return {
          session: next,
          step: getStepAfterMessageUpdate(state.step),
        };
      }
      if ('content' in message) {
        const next = mergeDiscussionMessage(session, round === 'round_2' ? 1 : 2, message);
        return {
          session: next,
          step: getStepAfterMessageUpdate(state.step),
          currentRound: state.step === 'discussion'
            ? Math.min(state.currentRound, Math.max(next.rounds.length, 1))
            : state.currentRound,
        };
      }
      return state;
    });
    return;
  }

  if (event.event_type === 'completed') {
    const response = event.payload.response as BackendConsultationResponse;
    applyBackendResponse(response, set, get, { preserveStep: true });
    get().eventSource?.close();
    set({ eventSource: null });
    return;
  }

  if (event.event_type === 'error_occurred') {
    set({ errorMessage: '상담 처리 중 일부 문제가 있었어요. 가능한 결과를 계속 정리하고 있습니다.' });
  }
}

function applyBackendResponse(
  response: BackendConsultationResponse,
  set: typeof useConsultationStore.setState,
  get: typeof useConsultationStore.getState,
  options: { preserveStep: boolean },
) {
  const session = mapBackendResponseToSession(response);
  const current = get();
  const stepForDisplay = getStepAfterResponse(
    response.status,
    session,
    options.preserveStep ? current.step : 'loading',
  );

  set({
    session,
    backendStatus: response.status,
    step: stepForDisplay,
    currentRound: stepForDisplay === 'discussion'
      ? Math.min(current.currentRound, Math.max(session.rounds.length, 1))
      : 1,
  });
}

function getStepAfterResponse(
  status: BackendStatus,
  session: ConsultationSession | null,
  currentStep: ConsultationStep,
): ConsultationStep {
  if (status === 'failed') return 'loading';
  if (!session || session.opinions.length === 0) return 'loading';

  if (currentStep === 'discussion') return 'discussion';
  if (currentStep === 'result' && session.finalResult) return 'result';
  return 'opinions';
}

function getStepAfterStatusUpdate(
  status: BackendStatus,
  session: ConsultationSession | null,
  currentStep: ConsultationStep,
): ConsultationStep {
  if (status === 'failed') return 'loading';
  if (currentStep !== 'loading') return currentStep;
  return session?.opinions.length ? 'opinions' : 'loading';
}

function getStepAfterMessageUpdate(currentStep: ConsultationStep): ConsultationStep {
  if (currentStep === 'input' || currentStep === 'loading') return 'opinions';
  return currentStep;
}
