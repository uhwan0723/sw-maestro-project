type UserChatProps = { text: string }
export function UserChat ({ text }: UserChatProps) {
  return (
    <div className='max-w-[88%] self-end rounded-2xl bg-blue-600 px-4 py-2 text-white'>
      <span className='whitespace-pre-line break-words'>{text}</span>
    </div>
  )
}
