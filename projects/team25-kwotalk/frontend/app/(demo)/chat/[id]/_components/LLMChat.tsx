'use client'

import type { Citation, RetrievedDoc } from '@/app/_lib/chat'
import { LucideCopy, RefreshCwIcon, Share2Icon } from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { defaultUrlTransform } from 'react-markdown'
import ReactMarkdown from 'react-markdown'
import type { Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

const CITATION_TOOLTIP_WIDTH = 320
const CITATION_TOOLTIP_GAP = 8
const CITATION_TOOLTIP_MARGIN = 12
const CITATION_TOOLTIP_EXIT_MS = 200

function ToolButton ({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  onClick?: () => void
}) {
  return (
    <button
      type='button'
      aria-label={label}
      onClick={onClick}
      className='p-2 rounded-full cursor-pointer text-app-muted hover:bg-surface-muted'
    >
      {icon}
    </button>
  )
}

function ProgressStatus ({ label }: { label: string }) {
  return (
    <span className='chat-progress-status'>
      <span className='chat-progress-dot' aria-hidden='true' />
      <span>{label}</span>
    </span>
  )
}

type ReferencedDoc = {
  markerIdx: number
  doc: RetrievedDoc
}

function getDocsByMarker (
  citations: Citation[] | undefined,
  retrievedDocs: RetrievedDoc[] | undefined
) {
  const docsByMarker = new Map<number, RetrievedDoc>()
  if (citations === undefined || retrievedDocs === undefined) return docsByMarker

  const docsById = new Map(retrievedDocs.map((doc) => [doc.doc_id, doc]))

  for (const citation of citations) {
    const doc = docsById.get(citation.doc_id)
    if (doc === undefined) continue

    docsByMarker.set(citation.marker_idx, doc)
  }

  return docsByMarker
}

function markCitationPreviews (
  text: string,
  docsByMarker: Map<number, RetrievedDoc>
) {
  if (docsByMarker.size === 0) return text

  return text.replace(/\[(\d+)\]/g, (match, rawMarker) => {
    const markerIdx = Number(rawMarker)

    if (!docsByMarker.has(markerIdx)) return match

    return `[${rawMarker}](citation:${rawMarker})`
  })
}

function CitationPreview ({ markerIdx, doc }: ReferencedDoc) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const tooltipRef = useRef<HTMLSpanElement>(null)
  const closeTimeoutRef = useRef<number | null>(null)
  const openFrameRef = useRef<number | null>(null)
  const [isPreviewMounted, setIsPreviewMounted] = useState(false)
  const [isPreviewVisible, setIsPreviewVisible] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 })

  useLayoutEffect(() => {
    if (!isPreviewMounted) return

    function updateTooltipPosition () {
      const button = buttonRef.current
      const tooltip = tooltipRef.current

      if (button === null || tooltip === null) return

      const buttonRect = button.getBoundingClientRect()
      const tooltipRect = tooltip.getBoundingClientRect()
      const tooltipWidth = Math.min(CITATION_TOOLTIP_WIDTH, window.innerWidth - CITATION_TOOLTIP_MARGIN * 2)
      const preferredLeft = buttonRect.left + buttonRect.width / 2 - tooltipWidth / 2
      const left = Math.min(
        Math.max(CITATION_TOOLTIP_MARGIN, preferredLeft),
        window.innerWidth - tooltipWidth - CITATION_TOOLTIP_MARGIN
      )
      const topAbove = buttonRect.top - tooltipRect.height - CITATION_TOOLTIP_GAP
      const topBelow = buttonRect.bottom + CITATION_TOOLTIP_GAP
      const top = topAbove >= CITATION_TOOLTIP_MARGIN ? topAbove : topBelow

      setTooltipPosition({ top, left })
    }

    updateTooltipPosition()
    window.addEventListener('resize', updateTooltipPosition)
    window.addEventListener('scroll', updateTooltipPosition, true)

    return () => {
      window.removeEventListener('resize', updateTooltipPosition)
      window.removeEventListener('scroll', updateTooltipPosition, true)
    }
  }, [isPreviewMounted])

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current !== null) {
        window.clearTimeout(closeTimeoutRef.current)
      }

      if (openFrameRef.current !== null) {
        window.cancelAnimationFrame(openFrameRef.current)
      }
    }
  }, [])

  function openPreview () {
    if (closeTimeoutRef.current !== null) {
      window.clearTimeout(closeTimeoutRef.current)
      closeTimeoutRef.current = null
    }

    if (openFrameRef.current !== null) {
      window.cancelAnimationFrame(openFrameRef.current)
    }

    setIsPreviewMounted(true)
    openFrameRef.current = window.requestAnimationFrame(() => {
      openFrameRef.current = window.requestAnimationFrame(() => {
        setIsPreviewVisible(true)
        openFrameRef.current = null
      })
    })
  }

  function closePreview () {
    if (openFrameRef.current !== null) {
      window.cancelAnimationFrame(openFrameRef.current)
      openFrameRef.current = null
    }

    setIsPreviewVisible(false)

    closeTimeoutRef.current = window.setTimeout(() => {
      setIsPreviewMounted(false)
      closeTimeoutRef.current = null
    }, CITATION_TOOLTIP_EXIT_MS)
  }

  return (
    <span className='inline-flex align-baseline rounded-4xl'>
      <button
        ref={buttonRef}
        type='button'
        onMouseEnter={openPreview}
        onMouseLeave={closePreview}
        onFocus={openPreview}
        onBlur={closePreview}
        className='mx-0.5 inline-flex -translate-y-px items-center rounded bg-blue-500/10 px-0.5 py-0.5 text-xs font-semibold text-blue-600 transition-colors duration-200 hover:bg-blue-500/15 focus-visible:bg-blue-500/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 dark:text-blue-300 cursor-pointer'
        aria-label={`참고 문서 ${markerIdx}: ${doc.title}`}
      >
        [{markerIdx}]
      </button>
      {isPreviewMounted && createPortal(
        <span
          ref={tooltipRef}
          className={`pointer-events-none fixed w-80 max-w-[calc(100vw-3rem)] rounded-md border border-app-border bg-panel p-3 text-left text-sm leading-6 text-app-text shadow-xl transition-opacity duration-200 ease-out will-change-[opacity] ${
            isPreviewVisible ? 'opacity-100' : 'opacity-0'
          }`}
          style={{
            top: tooltipPosition.top,
            left: tooltipPosition.left,
            zIndex: 1000,
          }}
        >
          <span className='mb-1 flex items-center gap-2'>
            <span className='rounded bg-surface-muted px-1.5 py-0.5 text-xs text-app-muted'>
              {doc.type}
            </span>
          </span>
          <span className='block font-semibold text-app-text'>{doc.title}</span>
          <span className='mt-1 block text-app-muted leading-[1.3]'>{doc.content}</span>
          <span className='mt-2 block text-xs text-app-subtle font-base'>
            유사도 {doc.score.toFixed(3)}
          </span>
        </span>,
        document.body
      )}
    </span>
  )
}

function transformMarkdownUrl (url: string) {
  if (url.startsWith('citation:')) return url

  return defaultUrlTransform(url)
}

export function LLMChat ({
  text,
  isStreaming = false,
  isError = false,
  progressLabel,
  retrievedDocs,
  citations,
  onRetry,
}: {
  text: string
  isStreaming?: boolean
  isError?: boolean
  progressLabel?: string
  retrievedDocs?: RetrievedDoc[]
  citations?: Citation[]
  onRetry?: () => void
}) {
  const hasText = text.length > 0
  const statusText = progressLabel ?? '답변을 작성하고 있어요...'
  const docsByMarker = useMemo(
    () => getDocsByMarker(citations, retrievedDocs),
    [citations, retrievedDocs]
  )
  const renderedMarkdown = useMemo(
    () => markCitationPreviews(text, docsByMarker),
    [docsByMarker, text]
  )
  const markdownComponents: Components = {
    h2: ({ children }) => (
      <h2 className='mt-5 text-lg font-bold first:mt-0'>{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className='mt-4 text-base font-semibold'>{children}</h3>
    ),
    p: ({ children }) => (
      <p className='my-2 leading-7'>{children}</p>
    ),
    ul: ({ children }) => (
      <ul className='my-2 list-disc space-y-1 pl-5'>{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className='my-2 list-decimal space-y-1 pl-5'>{children}</ol>
    ),
    li: ({ children }) => (
      <li className='leading-7'>{children}</li>
    ),
    strong: ({ children }) => (
      <strong className='font-semibold text-app-text'>{children}</strong>
    ),
    hr: () => (
      <hr className='my-5 border-app-border' />
    ),
    a: ({ href, children }) => {
      if (href?.startsWith('citation:') === true) {
        const markerIdx = Number(href.slice('citation:'.length))
        const doc = docsByMarker.get(markerIdx)

        if (doc === undefined) return <>{children}</>

        return (
          <CitationPreview markerIdx={markerIdx} doc={doc} />
        )
      }

      return (
        <a
          href={href}
          target='_blank'
          rel='noreferrer'
          className='font-medium underline underline-offset-2'
        >
          {children}
        </a>
      )
    }
  }

  return (
    <div className='flex flex-col self-start py-2'>
      {isStreaming && !hasText
        ? (
          <ProgressStatus label={statusText} />
          )
        : (
          <div className={`wrap-break-word ${isError ? 'text-red-500' : ''}`}>
            {hasText
              ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                  urlTransform={transformMarkdownUrl}
                >
                  {renderedMarkdown}
                </ReactMarkdown>
                )
              : '답변을 불러오지 못했습니다.'}
          </div>
          )}
      {isStreaming && hasText && progressLabel !== undefined && (
        <div className='mt-4'>
          <ProgressStatus label={progressLabel} />
        </div>
      )}
      {(hasText || isError) && (
        <div className='flex justify-start mt-2 -ml-2'>
          <ToolButton label='답변 복사' icon={<LucideCopy size={16} />} />
          <ToolButton label='답변 공유' icon={<Share2Icon size={16} />} />
          <ToolButton
            label={isError ? '답변 재시도' : '답변 다시 생성'}
            icon={<RefreshCwIcon size={16} />}
            onClick={onRetry}
          />
        </div>
      )}
    </div>
  )
}
