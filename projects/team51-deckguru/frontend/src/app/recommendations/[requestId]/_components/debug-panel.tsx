import type { RecommendationResponse } from '@/lib/schema';

import { PANEL_CLASS_NAME } from './recommendation-result-shared';

export function DebugPanel({
  debug,
}: {
  debug: RecommendationResponse['debug'];
}) {
  if (!debug) {
    return null;
  }

  return (
    <details className={`${PANEL_CLASS_NAME} p-5`}>
      <summary className="cursor-pointer font-galmuri11 text-sm font-bold text-primary">
        진단 정보
      </summary>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <DebugMetric label="React 단계" value={`${debug.react_steps}`} />
        <DebugMetric
          label="RAG 평균 점수"
          value={debug.rag_avg_score.toFixed(2)}
        />
        <DebugMetric
          label="Tier 2 검색"
          value={debug.tier2_triggered ? '사용' : '미사용'}
        />
        <DebugMetric
          label="노드 수"
          value={`${Object.keys(debug.node_latencies_ms).length}`}
        />
      </dl>
    </details>
  );
}

function DebugMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-galmuri11 text-[10px] font-bold text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-foreground">{value}</dd>
    </div>
  );
}
