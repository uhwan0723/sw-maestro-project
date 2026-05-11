import type { RecommendationResponse } from '@/lib/schema';

import { DebugPanel } from './debug-panel';
import { MetaBrief } from './meta-brief';
import { RecommendationDecksSection } from './recommendation-decks-section';
import { ResultHeader } from './result-header';
import { SourcesPanel } from './sources-panel';
import { WarningsPanel } from './warnings-panel';

interface RecommendationResultViewProps {
  recommendation: RecommendationResponse;
}

export function RecommendationResultView({
  recommendation,
}: RecommendationResultViewProps) {
  return (
    <main className="pixel-background relative isolate min-h-dvh w-full overflow-x-hidden px-4 py-6 text-foreground sm:px-8">
      <section className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-6">
        <ResultHeader recommendation={recommendation} />
        <MetaBrief recommendation={recommendation} />
        <RecommendationDecksSection decks={recommendation.decks} />
        <WarningsPanel warnings={recommendation.warnings} />
        <SourcesPanel sources={recommendation.sources} />
        <DebugPanel debug={recommendation.debug} />
      </section>
    </main>
  );
}
