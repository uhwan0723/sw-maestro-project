'use client'

type PromptChipProps = {
  label: string
  onClick: () => void
}

export default function PromptChip ({ label, onClick }: PromptChipProps) {
  return (
    <button
      type='button'
      onClick={onClick}
      className='cursor-pointer rounded-full border border-app-border bg-panel px-4 py-2 text-sm text-app-muted transition-colors duration-200 hover:bg-surface-muted hover:text-app-text'
    >
      {label}
    </button>
  )
}
