'use client'

import Link from 'next/link'
import { MenuIcon, PencilLine, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import Image from 'next/image'
import { usePathname } from 'next/navigation'

import { getChatSessions, subscribeChatSessions } from '../_lib/chat'
import ThemeToggle from './ThemeToggle'

type ChatItemProps = {
  title: string
  isActive?: boolean
  href: string
  onClick?: () => void
}

function ChatItem ({ title, isActive = false, href, onClick }: ChatItemProps) {
  return (
    <li>
      <Link href={href} onClick={onClick}>
        <div
          className={`
          flex w-full cursor-pointer items-center gap-3 rounded-md 
          px-3 py-2.5 text-left transition-colors duration-200 ${
          isActive
            ? 'bg-surface-muted text-app-text'
            : 'text-app-muted hover:bg-surface-muted hover:text-app-text'
        }`}
        >
          <span className='min-w-0'>
            <span className='block text-sm font-medium truncate'>{title}</span>
          </span>
        </div>
      </Link>
    </li>
  )
}

type SidebarContentProps = {
  collapsed: boolean
  onNewChatClick?: () => void
  onHeaderButtonClick: () => void
  toggleLabel: string
  toggleIcon?: 'menu' | 'close'
  chats: Array<{ id: string, title: string }>
  activePathname: string
}

function SidebarContent ({
  collapsed,
  onNewChatClick,
  onHeaderButtonClick,
  toggleLabel,
  toggleIcon = 'menu',
  chats,
  activePathname,
}: SidebarContentProps) {
  const ToggleIcon = toggleIcon === 'close' ? X : MenuIcon

  return (
    <>
      <div
        className={`mb-3 flex ${
          collapsed ? 'flex-col items-center gap-2 px-0' : 'items-center gap-1'
        }`}
      >
        <Link href='/'>
          <Image src='/logo.png' alt='Logo' width={40} height={40} />
        </Link>

        {!collapsed && (
          <Link href='/' className='min-w-0'>
            <div className='min-w-0'>
              <h2 className='text-lg font-bold truncate'>교톡</h2>
            </div>
          </Link>
        )}

        <button
          type='button'
          aria-label={toggleLabel}
          onClick={onHeaderButtonClick}
          className={`flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-app-muted transition-colors duration-200 hover:bg-surface-muted hover:text-app-text ${
            collapsed ? '' : 'ml-auto'
          }`}
        >
          <ToggleIcon size={18} />
        </button>
      </div>

      <Link
        href='/'
        onClick={onNewChatClick}
        className={`mb-3 flex h-10 items-center w-full gap-2 px-3 text-sm font-semibold transition-colors duration-200
                 hover:bg-surface-muted hover:text-app-text rounded-md
                 ${collapsed ? 'text-app-muted' : ''}`}
        aria-label='새 채팅'
      >
        <PencilLine size={17} />
        {!collapsed && <span>새 채팅</span>}
      </Link>

      {!collapsed && (
        <section className='flex-1 min-h-0'>
          <div className='px-2 mb-2 text-xs font-medium text-app-subtle'>
            최근 대화
          </div>
          <ul className='space-y-1'>
            {chats.length === 0 && (
              <li className='px-3 py-2 text-sm text-app-subtle'>
                저장된 대화가 없습니다
              </li>
            )}
            {chats.map((chat) => (
              <ChatItem
                key={chat.id}
                href={`/chat/${chat.id}`}
                title={chat.title}
                isActive={activePathname === `/chat/${chat.id}`}
                onClick={onNewChatClick}
              />
            ))}
          </ul>
        </section>
      )}
      {collapsed && <div className='flex-1' />}
      <ThemeToggle />
    </>
  )
}

export default function AppSidebar () {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [chats, setChats] = useState<Array<{ id: string, title: string }>>([])

  useEffect(() => {
    function syncChats () {
      setChats(getChatSessions().map((session) => ({
        id: session.id,
        title: session.title,
      })))
    }

    syncChats()
    return subscribeChatSessions(syncChats)
  }, [])

  const onClickCollapse = () => {
    setCollapsed((prev) => !prev)
  }

  const openMobileSidebar = () => {
    setMobileOpen(true)
  }

  const closeMobileSidebar = () => {
    setMobileOpen(false)
  }

  return (
    <>
      {!mobileOpen && (
        <button
          type='button'
          aria-label='사이드바 열기'
          onClick={openMobileSidebar}
          className='fixed z-40 flex items-center justify-center transition-colors duration-200 border rounded-md shadow-lg cursor-pointer left-4 top-4 size-10 border-app-border bg-panel text-app-text hover:bg-surface-muted md:hidden'
        >
          <MenuIcon size={20} />
        </button>
      )}

      {mobileOpen && (
        <button
          type='button'
          aria-label='사이드바 닫기'
          onClick={closeMobileSidebar}
          className='fixed inset-0 z-40 cursor-default bg-app-overlay md:hidden'
        />
      )}

      <nav
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden border-r border-app-border bg-panel px-3 py-4 text-app-text shadow-2xl transition-transform duration-200 ease-in-out md:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <SidebarContent
          collapsed={false}
          onNewChatClick={closeMobileSidebar}
          onHeaderButtonClick={closeMobileSidebar}
          toggleLabel='사이드바 닫기'
          toggleIcon='close'
          chats={chats}
          activePathname={pathname}
        />
      </nav>

      <nav
        className={`hidden h-screen flex-col overflow-hidden border-r border-app-border bg-panel px-3 py-4 text-app-text transition-[width] duration-200 ease-in-out md:flex ${
          collapsed ? 'w-16' : 'w-72'
        }`}
      >
        <SidebarContent
          collapsed={collapsed}
          onHeaderButtonClick={onClickCollapse}
          toggleLabel={collapsed ? '사이드바 열기' : '사이드바 닫기'}
          chats={chats}
          activePathname={pathname}
        />
      </nav>
    </>
  )
}
