'use client'

import { useRouter } from 'next/navigation'
import { useRef } from 'react'

import { createChatSession, saveChatSession } from '../_lib/chat'
import ChatInputBox from './ChatInputBox'
import type { ChatInputBoxHandle } from './ChatInputBox'
import PromptChip from './PromptChip'

const promptSuggestions = [
  '과실비율이 뭔가요?',
  '합의금은 어떻게 정해지나요?',
  '우회전하던 차와 부딪혔는데 과실비율은 어떻게 되나요?',
  '교통사고 합의금 계산 방법을 알려주세요.',
  '교통사고 과실비율은 어떻게 결정되나요?',
]

export default function StartChat () {
  const router = useRouter()
  const chatInputRef = useRef<ChatInputBoxHandle>(null)

  function handlePromptClick (prompt: string) {
    chatInputRef.current?.setMessage(prompt)
    chatInputRef.current?.focus()
  }

  function handleSend (message: string) {
    const session = createChatSession(message)

    saveChatSession(session)
    router.push(`/chat/${session.id}`)
  }

  return (
    <div className='mx-auto flex h-full w-full max-w-3xl flex-col justify-center gap-10 px-6 text-app-text'>
      <section className='flex flex-col items-start gap-1'>
        <p className='text-app-muted'>안녕하세요, 사용자님!</p>
        <h1 className='text-3xl font-bold'>무엇을 도와드릴까요?</h1>
      </section>

      <div className='flex flex-col gap-4'>
        <div className='flex flex-wrap gap-2'>
          {promptSuggestions.map((prompt) => (
            <PromptChip
              key={prompt}
              label={prompt}
              onClick={() => handlePromptClick(prompt)}
            />
          ))}
        </div>
        <ChatInputBox
          ref={chatInputRef}
          onSend={handleSend}
        />
      </div>
    </div>
  )
}
