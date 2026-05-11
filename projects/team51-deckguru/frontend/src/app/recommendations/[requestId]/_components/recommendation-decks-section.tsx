import type { DeckRecommendation } from '@/lib/schema';
import { WarningIcon } from '@phosphor-icons/react';

import { DeckCard } from './deck-card';
import {
  PANEL_CLASS_NAME,
  SectionEyebrow,
} from './recommendation-result-shared';

export function RecommendationDecksSection({
  decks,
}: {
  decks: DeckRecommendation[];
}) {
  return (
    <section
      className="grid gap-5"
      aria-labelledby="recommendation-decks-title">
      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-1">
          <p className="font-galmuri11 text-xs font-bold text-primary">
            DECK ROUTES
          </p>
          <h2
            id="recommendation-decks-title"
            className="font-galmuri11 text-lg font-bold sm:text-xl">
            추천 덱 경로
          </h2>
        </div>
      </div>

      {decks.length > 0 ? (
        decks.map((deck, index) => (
          <DeckCard deck={deck} index={index} key={`${deck.name}-${index}`} />
        ))
      ) : (
        <NoDeckPanel />
      )}
    </section>
  );
}

function NoDeckPanel() {
  return (
    <section className={`${PANEL_CLASS_NAME} p-6 text-center`}>
      <SectionEyebrow icon={WarningIcon}>NO DECK DATA</SectionEyebrow>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        이번 응답에는 추천 덱이 포함되지 않았습니다. 메타 요약과 출처를 먼저
        확인해 주세요.
      </p>
    </section>
  );
}
