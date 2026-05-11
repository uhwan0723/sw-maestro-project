import { useEffect, useRef } from 'react'

type ChatViewProps = { children: React.ReactNode }
export function ChatView ({ children }: ChatViewProps) {
  const chatContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const chatContainer = chatContainerRef.current

    if (chatContainer !== null) {
      chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [children])

  return (
    <div ref={chatContainerRef} className='flex flex-col flex-1 w-full min-h-0 gap-10 py-10 overflow-y-auto text-app-text'>
      <div className='flex flex-col w-full gap-10 px-6 md:px-20'>
        {children}
      </div>
    </div>
  )
}
