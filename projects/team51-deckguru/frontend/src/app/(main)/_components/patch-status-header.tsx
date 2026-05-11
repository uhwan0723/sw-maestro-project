'use client';

import { usePatchInfoQuery } from '@/api/get-patch-info/query';
import { formatDateTime } from '@/app/recommendations/[requestId]/_lib/recommendation-result-formatters';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { PatchInfo } from '@/lib/schema';
import { ListIcon } from '@phosphor-icons/react';

type PatchInfoItem = {
  label: string;
  value: string;
};

const FALLBACK_PATCH_INFO: PatchInfo = {
  patch_version: 'unknown',
  last_updated: 'unknown',
  warnings: ['patch_info_unavailable'],
};

const STATUS_BADGE_CLASS =
  'h-9 border-2 px-3 py-2 text-[10px] whitespace-nowrap';
const PATCH_INFO_BADGE_CLASS = `${STATUS_BADGE_CLASS} backdrop-blur`;

export function PatchStatusHeader() {
  const { data, isError } = usePatchInfoQuery();
  const patchInfo = data ?? FALLBACK_PATCH_INFO;
  const hasWarnings = data ? patchInfo.warnings.length > 0 : isError;
  const patchInfoItems: PatchInfoItem[] = [
    {
      label: 'PATCH VERSION',
      value: patchInfo.patch_version,
    },
    {
      label: 'LAST UPDATED',
      value: formatDateTime(patchInfo.last_updated),
    },
  ];

  return (
    <header className="relative z-20 flex h-16 w-full shrink-0 items-center justify-end px-4 sm:px-6">
      <div className="flex max-w-full items-center justify-end gap-2 sm:hidden">
        {hasWarnings ? <DataWarningBadge /> : null}
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="패치 정보 열기"
            className="inline-flex size-9 items-center justify-center rounded-none border-2 border-border bg-background/70 text-foreground backdrop-blur transition-colors outline-none select-none hover:bg-muted focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50 aria-expanded:bg-muted">
            <ListIcon aria-hidden weight="bold" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            sideOffset={8}
            className="w-60 border-2 border-border bg-background/95 p-2 backdrop-blur">
            <div className="px-2 py-1 text-[10px] text-muted-foreground">
              PATCH INFO
            </div>
            <DropdownMenuSeparator className="my-1" />
            <PatchInfoMenuItems items={patchInfoItems} />
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="hidden max-w-full flex-wrap items-center justify-end gap-2 sm:flex">
        {hasWarnings ? <DataWarningBadge /> : null}
        <StatusBadge>PATCH VERSION {patchInfoItems[0].value}</StatusBadge>
        <StatusBadge>LAST UPDATED {patchInfoItems[1].value}</StatusBadge>
      </div>
    </header>
  );
}

function StatusBadge({
  variant = 'outline',
  children,
}: {
  variant?: 'destructive' | 'outline';
  children: React.ReactNode;
}) {
  return (
    <Badge
      variant={variant}
      className={
        variant === 'destructive' ? STATUS_BADGE_CLASS : PATCH_INFO_BADGE_CLASS
      }>
      {children}
    </Badge>
  );
}

function DataWarningBadge() {
  return <StatusBadge variant="destructive">DATA WARNING</StatusBadge>;
}

function PatchInfoMenuItems({ items }: { items: PatchInfoItem[] }) {
  return (
    <div className="grid gap-1">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center justify-between gap-4 px-2 py-2">
          <span className="text-[10px] text-muted-foreground">
            {item.label}
          </span>
          <span className="text-xs font-medium whitespace-nowrap text-foreground">
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
}
