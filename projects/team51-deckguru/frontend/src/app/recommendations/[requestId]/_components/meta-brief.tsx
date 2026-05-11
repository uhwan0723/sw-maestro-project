import type { RecommendationResponse } from '@/lib/schema';
import {
  GameControllerIcon,
  GaugeIcon,
  ListChecksIcon,
  SparkleIcon,
  TreeStructureIcon,
} from '@phosphor-icons/react';

import { CONFIDENCE_CONFIG } from '../_lib/recommendation-result-appearance';
import { formatDateTime } from '../_lib/recommendation-result-formatters';
import { INTENT_LABEL } from '../_lib/recommendation-result-labels';
import {
  type IconComponent,
  PANEL_CLASS_NAME,
  SectionEyebrow,
} from './recommendation-result-shared';

export function MetaBrief({
  recommendation,
}: {
  recommendation: RecommendationResponse;
}) {
  const confidence = CONFIDENCE_CONFIG[recommendation.confidence];

  return (
    <section
      className={`${PANEL_CLASS_NAME} overflow-hidden`}
      aria-labelledby="meta-brief-title">
      <div className="grid gap-0 lg:grid-cols-[minmax(0,1.35fr)_minmax(17rem,0.65fr)]">
        <div className="flex flex-col gap-4 p-5 sm:p-6">
          <SectionEyebrow icon={SparkleIcon}>메타 요약</SectionEyebrow>
          <div className="flex flex-col gap-3">
            <h2
              id="meta-brief-title"
              className="font-galmuri11 text-lg font-bold sm:text-xl">
              이번 판의 큰 방향
            </h2>
            <p className="text-sm leading-7 text-foreground/90 sm:text-base">
              {recommendation.meta_summary}
            </p>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-x-5 gap-y-4 border-t-4 border-border bg-muted/20 p-5 sm:p-6 lg:border-t-0 lg:border-l-4">
          <ResultMetric
            icon={GameControllerIcon}
            label="패치"
            value={recommendation.patch_version}
          />
          <ResultMetric
            icon={GaugeIcon}
            label="신뢰도"
            value={confidence.label}
            valueClassName={confidence.className}
          />
          <ResultMetric
            icon={TreeStructureIcon}
            label="요청 유형"
            value={INTENT_LABEL[recommendation.intent]}
          />
          <ResultMetric
            icon={ListChecksIcon}
            label="추천 수"
            value={`${recommendation.decks.length}개`}
          />
          <div className="col-span-2 border-t-2 border-border/70 pt-4">
            <dt className="mb-1 font-galmuri11 text-[10px] font-bold text-muted-foreground">
              생성 시각
            </dt>
            <dd className="text-sm leading-6 text-foreground">
              {formatDateTime(recommendation.generated_at)}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}

function ResultMetric({
  icon: Icon,
  label,
  value,
  valueClassName,
}: {
  icon: IconComponent;
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <dt className="flex items-center gap-1.5 font-galmuri11 text-[10px] font-bold text-muted-foreground">
        <Icon aria-hidden className="size-3.5 text-primary" weight="bold" />
        {label}
      </dt>
      <dd
        className={
          valueClassName
            ? `w-fit border-2 px-2 py-1 font-galmuri11 text-xs font-bold ${valueClassName}`
            : 'truncate font-galmuri11 text-sm font-bold text-foreground'
        }>
        {value}
      </dd>
    </div>
  );
}
