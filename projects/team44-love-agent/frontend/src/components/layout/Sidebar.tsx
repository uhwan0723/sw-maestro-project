'use client';

// 사이드바 — 네비게이션, 에이전트 목록
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { HelpCircle, History, MessageCirclePlus, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { AgentAvatar } from '@/components/agents';
import { useConsultationStore } from '@/stores/consultationStore';
import type { Agent } from '@/types';
import { resultContent } from '@/content';

type NavAction = 'new' | 'route';

const NAV_ITEMS: { icon: LucideIcon; label: string; action: NavAction; href?: string }[] = [
  { icon: MessageCirclePlus, label: '새로운 상담', action: 'new' },
  { icon: History, label: '상담 기록', action: 'route', href: '/history' },
  { icon: Users, label: '에이전트 소개', action: 'route', href: '/agents' },
  { icon: HelpCircle, label: '사용 방법', action: 'route', href: '/guide' },
];

interface SidebarProps {
  agents: Agent[];
}

export function Sidebar({ agents }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const reset = useConsultationStore((s) => s.reset);

  function handleNavClick(item: (typeof NAV_ITEMS)[number]) {
    if (item.action === 'new') {
      reset();
      router.push('/');
      return;
    }

    if (item.href) {
      router.push(item.href);
    }
  }

  function handleLogoClick() {
    reset();
    router.push('/');
  }

  return (
    <aside className="flex w-52 shrink-0 flex-col border-r border-border bg-white">
      {/* 로고 */}
      <button
        onClick={handleLogoClick}
        className="flex items-center gap-2 px-4 py-4 text-left transition-opacity hover:opacity-80"
      >
        <Image src="/logo.png" alt="로고" width={28} height={28} className="rounded-md" />
        <span className="text-xs font-semibold leading-tight text-foreground">연애상담 멀티 에이전트</span>
      </button>

      <Separator />

      {/* 네비게이션 */}
      <nav className="flex flex-col gap-0.5 px-2 py-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.action === 'route' ? pathname === item.href : pathname === '/';
          return (
            <button
              key={item.label}
              onClick={() => handleNavClick(item)}
              aria-current={isActive ? 'page' : undefined}
              className={`flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                isActive
                  ? 'bg-accent text-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              }`}
            >
              <Icon className="size-4 shrink-0" />
              {item.label}
            </button>
          );
        })}
      </nav>

      <Separator />

      {/* 에이전트 목록 */}
      <ScrollArea className="flex-1 px-2 py-2">
        <p className="px-3 pb-1 pt-1 text-xs font-medium text-muted-foreground">상담 에이전트</p>
        <div className="flex flex-col gap-0.5">
          {agents.map((agent) => (
            <div key={agent.id} className="flex items-center gap-3 rounded-md px-3 py-2">
              <AgentAvatar agentId={agent.id} name={agent.name} colorKey={agent.colorKey} size="sm" />
              <div className="flex min-w-0 flex-col">
                <span className="truncate text-sm font-medium">{agent.name}</span>
                <span className="truncate text-xs text-muted-foreground">{agent.tone}</span>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* 하단 안내 */}
      <div className="border-t px-4 py-3">
        <p className="text-xs text-muted-foreground">{resultContent.sidebarDisclaimer}</p>
      </div>
    </aside>
  );
}
