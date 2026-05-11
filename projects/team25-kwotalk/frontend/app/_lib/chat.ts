export type ChatRole = 'user' | 'assistant'

export type ChatMessageStatus = 'streaming' | 'error'

export type ChatProgressNode =
  | 'classify'
  | 'clarify'
  | 'retrieve'
  | 'guide'
  | 'settlement'
  | 'generate'
  | 'post_check'
  | 'fallback'

export type RetrievedDoc = {
  doc_id: string
  type: '법령' | '판례' | '사례'
  title: string
  content: string
  case_types: string[]
  score: number
  settlement_amount: number | null
}

export type Citation = {
  marker_idx: number
  doc_id: string
}

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  status?: ChatMessageStatus
  progressNode?: ChatProgressNode
  progressLabel?: string
  retrievedDocs?: RetrievedDoc[]
  citations?: Citation[]
  error?: string
}

export type ChatSession = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
}

export type ChatHistoryMessage = {
  role: ChatRole
  content: string
}

type BackendChatRequest = {
  user_query: string
  session_id: string
  history: ChatHistoryMessage[]
}

export type ChatStreamEvent =
  | { type: 'meta', data: { phase?: string, node?: string } }
  | { type: 'token', data: { text?: string } }
  | { type: 'state', data: { node?: string, patch?: unknown } }
  | { type: 'done', data: Record<string, never> }
  | { type: 'error', data: { message?: string } }

type StreamChatParams = {
  sessionId: string
  userQuery: string
  history: ChatHistoryMessage[]
  signal?: AbortSignal
  onEvent: (event: ChatStreamEvent) => void
}

const CHAT_SESSIONS_STORAGE_KEY = 'gyotok.chat.sessions.v1'
export const CHAT_SESSIONS_UPDATED_EVENT = 'gyotok-chat-sessions-updated'

const EMPTY_CHAT_SESSIONS: ChatSession[] = []
let cachedStorageValue: string | null | undefined
let cachedChatSessions: ChatSession[] = EMPTY_CHAT_SESSIONS

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export function createId () {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function createChatMessage (
  role: ChatRole,
  content: string,
  status?: ChatMessageStatus
): ChatMessage {
  return {
    id: createId(),
    role,
    content,
    createdAt: new Date().toISOString(),
    status,
  }
}

export function createChatSession (firstMessage: string): ChatSession {
  const now = new Date().toISOString()

  return {
    id: createId(),
    title: makeSessionTitle(firstMessage),
    createdAt: now,
    updatedAt: now,
    messages: [createChatMessage('user', firstMessage)],
  }
}

export function makeSessionTitle (message: string) {
  const title = message.replace(/\s+/g, ' ').trim()

  if (title.length <= 28) return title

  return `${title.slice(0, 28)}...`
}

export function getChatSessions (): ChatSession[] {
  if (typeof window === 'undefined') return EMPTY_CHAT_SESSIONS

  const raw = window.localStorage.getItem(CHAT_SESSIONS_STORAGE_KEY)
  if (raw === cachedStorageValue) return cachedChatSessions

  cachedStorageValue = raw

  if (raw === null) {
    cachedChatSessions = EMPTY_CHAT_SESSIONS
    return cachedChatSessions
  }

  try {
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      cachedChatSessions = EMPTY_CHAT_SESSIONS
      return cachedChatSessions
    }

    cachedChatSessions = parsed.filter(isChatSession)
    return cachedChatSessions
  } catch {
    cachedChatSessions = EMPTY_CHAT_SESSIONS
    return cachedChatSessions
  }
}

export function getChatSession (sessionId: string) {
  return getChatSessions().find((session) => session.id === sessionId)
}

export function saveChatSession (session: ChatSession) {
  const sessions = getChatSessions()
  const nextSessions = [
    session,
    ...sessions.filter((item) => item.id !== session.id),
  ].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))

  saveChatSessions(nextSessions)
}

export function subscribeChatSessions (listener: () => void) {
  window.addEventListener(CHAT_SESSIONS_UPDATED_EVENT, listener)
  window.addEventListener('storage', listener)

  return () => {
    window.removeEventListener(CHAT_SESSIONS_UPDATED_EVENT, listener)
    window.removeEventListener('storage', listener)
  }
}

export function toBackendHistory (messages: ChatMessage[]): ChatHistoryMessage[] {
  return messages
    .filter((message) => message.status !== 'error')
    .filter((message) => message.content.trim().length > 0)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }))
}

export async function streamChat ({
  sessionId,
  userQuery,
  history,
  signal,
  onEvent,
}: StreamChatParams) {
  const body: BackendChatRequest = {
    user_query: userQuery,
    session_id: sessionId,
    history,
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    throw new Error(`채팅 요청에 실패했습니다. (${response.status})`)
  }

  if (response.body === null) {
    throw new Error('스트리밍 응답을 읽을 수 없습니다.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    buffer = emitSseEvents(buffer, onEvent)
  }

  buffer += decoder.decode()
  emitSseEvents(buffer, onEvent)
}

function saveChatSessions (sessions: ChatSession[]) {
  if (typeof window === 'undefined') return

  const nextStorageValue = JSON.stringify(sessions)

  cachedStorageValue = nextStorageValue
  cachedChatSessions = sessions
  window.localStorage.setItem(CHAT_SESSIONS_STORAGE_KEY, nextStorageValue)
  window.dispatchEvent(new Event(CHAT_SESSIONS_UPDATED_EVENT))
}

function emitSseEvents (
  buffer: string,
  onEvent: (event: ChatStreamEvent) => void
) {
  let rest = buffer

  while (true) {
    const delimiter = findSseDelimiter(rest)
    if (delimiter === null) return rest

    const rawEvent = rest.slice(0, delimiter.index)
    rest = rest.slice(delimiter.index + delimiter.length)
    const event = parseSseEvent(rawEvent)

    if (event !== null) {
      onEvent(event)
    }
  }
}

function findSseDelimiter (buffer: string) {
  const newlineIndex = buffer.indexOf('\n\n')
  const crlfIndex = buffer.indexOf('\r\n\r\n')

  if (newlineIndex === -1 && crlfIndex === -1) return null
  if (newlineIndex === -1) return { index: crlfIndex, length: 4 }
  if (crlfIndex === -1) return { index: newlineIndex, length: 2 }

  return newlineIndex < crlfIndex
    ? { index: newlineIndex, length: 2 }
    : { index: crlfIndex, length: 4 }
}

function parseSseEvent (rawEvent: string): ChatStreamEvent | null {
  const lines = rawEvent.split(/\r?\n/)
  const eventLine = lines.find((line) => line.startsWith('event:'))
  const dataLines = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice('data:'.length).trimStart())

  const type = eventLine?.slice('event:'.length).trim()
  if (type === undefined || dataLines.length === 0) return null

  const data: unknown = JSON.parse(dataLines.join('\n'))

  if (
    type === 'meta' ||
    type === 'token' ||
    type === 'state' ||
    type === 'done' ||
    type === 'error'
  ) {
    return { type, data } as ChatStreamEvent
  }

  return null
}

function isChatSession (value: unknown): value is ChatSession {
  if (typeof value !== 'object' || value === null) return false

  const candidate = value as Partial<ChatSession>

  return (
    typeof candidate.id === 'string' &&
    typeof candidate.title === 'string' &&
    typeof candidate.createdAt === 'string' &&
    typeof candidate.updatedAt === 'string' &&
    Array.isArray(candidate.messages) &&
    candidate.messages.every(isChatMessage)
  )
}

function isChatMessage (value: unknown): value is ChatMessage {
  if (typeof value !== 'object' || value === null) return false

  const candidate = value as Partial<ChatMessage>

  return (
    typeof candidate.id === 'string' &&
    (candidate.role === 'user' || candidate.role === 'assistant') &&
    typeof candidate.content === 'string' &&
    typeof candidate.createdAt === 'string'
  )
}
