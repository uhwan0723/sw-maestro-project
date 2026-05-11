import type { ReactNode } from 'react';

import { Badge } from '@/components/ui/badge';
import type { DeckRecommendation, Difficulty, Phase } from '@/lib/schema';
import {
  FlagCheckeredIcon,
  LightningIcon,
  ListChecksIcon,
  ShieldCheckIcon,
  SparkleIcon,
  TargetIcon,
  TrendUpIcon,
  WarningIcon,
} from '@phosphor-icons/react';

import { DIFFICULTY_CONFIG } from '../_lib/recommendation-result-appearance';
import {
  type IconComponent,
  PANEL_CLASS_NAME,
  SectionEyebrow,
} from './recommendation-result-shared';

const PHASE_CONFIG: Record<
  Phase,
  { label: string; icon: IconComponent; accentClassName: string }
> = {
  early: {
    label: '초반',
    icon: LightningIcon,
    accentClassName: 'text-emerald-200',
  },
  mid: {
    label: '중반',
    icon: TargetIcon,
    accentClassName: 'text-primary',
  },
  late: {
    label: '후반',
    icon: FlagCheckeredIcon,
    accentClassName: 'text-rose-200',
  },
};

export function DeckCard({
  deck,
  index,
}: {
  deck: DeckRecommendation;
  index: number;
}) {
  const difficulty = DIFFICULTY_CONFIG[deck.difficulty];

  return (
    <article className={`${PANEL_CLASS_NAME} overflow-hidden`}>
      <div className="flex flex-col gap-4 border-b-4 border-border bg-muted/20 p-5 sm:p-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-4">
          <div className="grid size-12 shrink-0 place-items-center border-4 border-primary bg-primary font-galmuri11 text-sm font-bold text-primary-foreground shadow-[4px_4px_0_0_rgb(0_0_0/0.45)]">
            {String(index + 1).padStart(2, '0')}
          </div>
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                className={`h-auto border-2 px-2 py-1 font-galmuri11 text-[10px] font-bold ${difficulty.className}`}>
                {difficulty.label}
              </Badge>
              <span className="font-galmuri11 text-[10px] font-bold text-muted-foreground">
                {difficulty.summary}
              </span>
            </div>
            <h3 className="font-galmuri11 text-xl font-bold break-keep text-foreground sm:text-2xl">
              {deck.name}
            </h3>
            <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
              {deck.rationale}
            </p>
          </div>
        </div>

        <DifficultyMeter difficulty={deck.difficulty} />
      </div>

      <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <div className="flex flex-col divide-y-4 divide-border/70">
          <DeckInfoSection icon={ShieldCheckIcon} title="핵심 유닛">
            <ChipList items={deck.core_units} />
          </DeckInfoSection>

          <DeckInfoSection icon={SparkleIcon} title="주요 아이템">
            <ChipList items={deck.key_items} tone="primary" />
          </DeckInfoSection>

          <DeckInfoSection icon={TrendUpIcon} title="증강체 방향">
            <p className="text-sm leading-6 text-foreground/90">
              {deck.augment_direction}
            </p>
          </DeckInfoSection>

          <DeckInfoSection icon={ListChecksIcon} title="운영 타임라인">
            <div className="grid gap-3 md:grid-cols-3">
              {deck.playbook.map((step) => (
                <PhaseStep
                  instruction={step.instruction}
                  key={`${deck.name}-${step.phase}`}
                  phase={step.phase}
                />
              ))}
            </div>
          </DeckInfoSection>
        </div>

        <aside className="flex flex-col gap-5 border-t-4 border-border bg-background/55 p-5 sm:p-6 lg:border-t-0 lg:border-l-4">
          <ConditionList
            icon={TargetIcon}
            items={deck.good_conditions}
            title="좋은 조건"
          />
          <ConditionList
            icon={WarningIcon}
            items={deck.avoid_conditions}
            title="주의 조건"
          />
          <div className="border-t-2 border-border/70 pt-5">
            <SectionEyebrow icon={FlagCheckeredIcon}>FALLBACK</SectionEyebrow>
            <p className="mt-3 text-sm leading-6 text-foreground/90">
              {deck.fallback_plan}
            </p>
          </div>
        </aside>
      </div>
    </article>
  );
}

function DifficultyMeter({ difficulty }: { difficulty: Difficulty }) {
  const config = DIFFICULTY_CONFIG[difficulty];

  return (
    <div
      className="flex shrink-0 items-center gap-2"
      aria-label={`운영 난이도 ${config.label}`}>
      <span className="font-galmuri11 text-[10px] font-bold text-muted-foreground">
        PILOT
      </span>
      <div className="flex gap-1" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, index) => (
          <span
            className={`block h-4 w-5 border-2 ${
              index < config.blocks
                ? 'border-primary bg-primary'
                : 'border-border bg-background/70'
            }`}
            key={index}
          />
        ))}
      </div>
    </div>
  );
}

function DeckInfoSection({
  children,
  icon,
  title,
}: {
  children: ReactNode;
  icon: IconComponent;
  title: string;
}) {
  return (
    <section className="flex flex-col gap-3 p-5 sm:p-6">
      <SectionEyebrow icon={icon}>{title}</SectionEyebrow>
      {children}
    </section>
  );
}

function ChipList({
  items,
  tone = 'default',
}: {
  items: string[];
  tone?: 'default' | 'primary';
}) {
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((item) => (
        <li key={item}>
          <Badge
            variant="outline"
            className={`h-9 max-w-full border-2 px-2.5 py-1.5 text-xs leading-5 break-keep whitespace-normal ${
              tone === 'primary'
                ? 'border-primary/70 bg-primary/15 text-primary'
                : 'border-border bg-muted/40 text-foreground'
            }`}>
            {item}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

function PhaseStep({
  instruction,
  phase,
}: {
  instruction: string;
  phase: Phase;
}) {
  const config = PHASE_CONFIG[phase];
  const Icon = config.icon;

  return (
    <div className="min-w-0 bg-muted/25 px-3 py-2.5 border-l-4">
      <div className="mb-2 flex items-center gap-1.5 font-galmuri11 text-[10px] font-bold">
        <Icon
          aria-hidden
          className={`size-3.5 ${config.accentClassName}`}
          weight="bold"
        />
        <span className={config.accentClassName}>{config.label}</span>
      </div>
      <p className="text-sm leading-6 text-foreground/90">{instruction}</p>
    </div>
  );
}

function ConditionList({
  icon: Icon,
  items,
  title,
}: {
  icon: IconComponent;
  items: string[];
  title: string;
}) {
  return (
    <section className="flex flex-col gap-3">
      <SectionEyebrow icon={Icon}>{title}</SectionEyebrow>
      {items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li
              className="flex gap-2 text-sm leading-6 text-foreground/90"
              key={item}>
              <span
                className="mt-2 block size-1.5 shrink-0 bg-primary"
                aria-hidden="true"
              />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm leading-6 text-muted-foreground">
          별도 주의 조건이 없습니다.
        </p>
      )}
    </section>
  );
}
