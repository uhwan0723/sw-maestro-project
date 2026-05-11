import type {
  AgentId,
  AgentOpinion,
  ConsultationSession,
  DiscussionMessage,
  DiscussionRound,
  FinalResult,
  StanceType,
} from '@/types';

export type BackendStatus =
  | 'pending'
  | 'analyzing'
  | 'round_1_running'
  | 'summary_1_running'
  | 'round_2_running'
  | 'classify_2_running'
  | 'round_3_running'
  | 'summarizing'
  | 'completed'
  | 'terminated'
  | 'failed';

type BackendRoundType = 'round_1' | 'round_2' | 'round_3';

interface BackendAgentOpinion {
  id: string;
  agent_id: AgentId;
  advice: string;
  rationale: string;
  stance: StanceType;
}

interface BackendAgentRebuttal {
  id: string;
  agent_id: AgentId;
  statement: string;
  targets?: Array<{ target_agent_id: AgentId }>;
}

interface BackendAgentFinalPosition {
  id: string;
  agent_id: AgentId;
  final_advice: string;
}

type BackendRoundMessage =
  | BackendAgentOpinion
  | BackendAgentRebuttal
  | BackendAgentFinalPosition;

interface BackendRound {
  round: BackendRoundType;
  messages: BackendRoundMessage[];
}

interface BackendFinal {
  situation: string;
  disagreements: string[];
  final_advice: string;
  action_items: FinalResult['actionItems'];
  caveats: string[];
}

export interface BackendConsultationResponse {
  consultation_id: string;
  status: BackendStatus;
  user_question: string;
  rounds: BackendRound[];
  final: BackendFinal | null;
}

const AGENT_IDS: AgentId[] = ['realist', 'empath', 'analyst', 'actor', 'mediator', 'friend'];

export function mapBackendResponseToSession(response: BackendConsultationResponse): ConsultationSession {
  return {
    userInput: response.user_question,
    opinions: response.rounds
      .filter((round) => round.round === 'round_1')
      .flatMap((round) => round.messages.map(mapOpinion).filter(Boolean) as AgentOpinion[]),
    rounds: response.rounds
      .filter((round) => round.round === 'round_2' || round.round === 'round_3')
      .map(mapDiscussionRound),
    finalResult: response.final ? mapFinal(response.final) : null,
  };
}

export function mapBackendMessage(round: BackendRoundType, message: BackendRoundMessage) {
  if (round === 'round_1') {
    return mapOpinion(message);
  }
  return mapDiscussionMessage(round, message);
}

export function mergeOpinion(session: ConsultationSession, opinion: AgentOpinion): ConsultationSession {
  if (session.opinions.some((item) => item.id === opinion.id)) {
    return session;
  }
  return { ...session, opinions: [...session.opinions, opinion] };
}

export function mergeDiscussionMessage(
  session: ConsultationSession,
  roundNumber: number,
  message: DiscussionMessage,
): ConsultationSession {
  const rounds = [...session.rounds];
  const index = rounds.findIndex((round) => round.roundNumber === roundNumber);
  if (index === -1) {
    rounds.push({ roundNumber, messages: [message] });
    return { ...session, rounds };
  }
  if (rounds[index].messages.some((item) => item.id === message.id)) {
    return session;
  }
  rounds[index] = {
    ...rounds[index],
    messages: [...rounds[index].messages, message],
  };
  return { ...session, rounds };
}

export function isTerminalStatus(status: BackendStatus) {
  return status === 'completed' || status === 'terminated' || status === 'failed';
}

function mapOpinion(message: BackendRoundMessage): AgentOpinion | null {
  if (!('advice' in message) || !isAgentId(message.agent_id)) {
    return null;
  }
  return {
    id: message.id,
    agentId: message.agent_id,
    advice: message.advice,
    rationale: message.rationale,
    stance: message.stance,
  };
}

function mapDiscussionRound(round: BackendRound): DiscussionRound {
  return {
    roundNumber: round.round === 'round_2' ? 1 : 2,
    messages: round.messages
      .map((message) => mapDiscussionMessage(round.round, message))
      .filter(Boolean) as DiscussionMessage[],
  };
}

function mapDiscussionMessage(round: BackendRoundType, message: BackendRoundMessage): DiscussionMessage | null {
  if (!isAgentId(message.agent_id)) {
    return null;
  }

  if (round === 'round_2' && 'statement' in message) {
    return {
      id: message.id,
      agentId: message.agent_id,
      content: message.statement,
      messageType: 'rebuttal',
      replyToAgentId: message.targets?.[0]?.target_agent_id,
    };
  }

  if (round === 'round_3' && 'final_advice' in message) {
    return {
      id: message.id,
      agentId: message.agent_id,
      content: message.final_advice,
      messageType: 'deepdive',
    };
  }

  return null;
}

function mapFinal(final: BackendFinal): FinalResult {
  return {
    situationSummary: final.situation,
    keyConflicts: final.disagreements,
    disagreements: final.disagreements,
    advice: final.final_advice,
    actionItems: final.action_items,
    caveats: final.caveats,
  };
}

function isAgentId(value: string): value is AgentId {
  return AGENT_IDS.includes(value as AgentId);
}
