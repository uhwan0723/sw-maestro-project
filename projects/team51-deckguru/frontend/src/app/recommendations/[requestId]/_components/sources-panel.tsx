import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Source } from '@/lib/schema';
import { ArrowSquareOutIcon } from '@phosphor-icons/react';

import {
  formatDateTime,
  getSourceDomain,
} from '../_lib/recommendation-result-formatters';
import { getSourceKindLabel } from '../_lib/recommendation-result-labels';
import { PANEL_CLASS_NAME } from './recommendation-result-shared';

export function SourcesPanel({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <section
      className="grid gap-5"
      aria-labelledby="recommendation-sources-title">
      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-1">
          <p className="font-galmuri11 text-xs font-bold text-primary">
            EVIDENCE
          </p>
          <h2
            id="recommendation-sources-title"
            className="font-galmuri11 text-lg font-bold sm:text-xl">
            추천 근거
          </h2>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {sources.map((source) => (
          <SourceCard key={`${source.title}-${source.url}`} source={source} />
        ))}
      </div>
    </section>
  );
}

function SourceCard({ source }: { source: Source }) {
  return (
    <article className={`${PANEL_CLASS_NAME} flex min-w-0 flex-col gap-4 p-5`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          variant="outline"
          className="h-auto border-2 border-primary/70 bg-primary/15 px-2 py-1 font-galmuri11 text-[10px] font-bold text-primary">
          {getSourceKindLabel(source.source_kind)}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {formatDateTime(source.published_at)}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <h3 className="font-galmuri11 text-base leading-7 font-bold break-keep text-foreground">
          {source.title}
        </h3>
        <p className="text-sm leading-6 text-muted-foreground">
          {source.snippet}
        </p>
      </div>

      <Button
        type="button"
        nativeButton={false}
        variant="outline"
        className="mt-auto h-11 w-full justify-between border-2 bg-background/80 px-3 font-galmuri11 text-xs font-bold"
        aria-label={`${source.title} 출처 열기`}
        render={
          <a href={source.url} target="_blank" rel="noreferrer noopener" />
        }>
        <span className="truncate">{getSourceDomain(source.url)}</span>
        <ArrowSquareOutIcon aria-hidden className="size-4" weight="bold" />
      </Button>
    </article>
  );
}
