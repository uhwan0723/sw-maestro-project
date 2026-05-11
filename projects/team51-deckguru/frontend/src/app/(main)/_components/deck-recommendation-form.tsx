import type { RefObject, SubmitEvent } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { PlayStyle, Tier } from '@/lib/schema';
import { CrosshairIcon, GameControllerIcon } from '@phosphor-icons/react';
import { m } from 'motion/react';

import { MAIN_PANEL_CLASS_NAME, MainSectionEyebrow } from './main-page-shared';

const TIER_OPTIONS: Array<{ value: Tier; label: string }> = [
  { value: 'IRON', label: '아이언' },
  { value: 'BRONZE', label: '브론즈' },
  { value: 'SILVER', label: '실버' },
  { value: 'GOLD', label: '골드' },
  { value: 'PLATINUM', label: '플래티넘' },
  { value: 'EMERALD', label: '에메랄드' },
  { value: 'DIAMOND', label: '다이아' },
  { value: 'MASTER+', label: '마스터+' },
];

const PLAY_STYLE_OPTIONS: Array<{ value: PlayStyle; label: string }> = [
  { value: 'flexible', label: '유동적인 운영형' },
  { value: 'stable_top4', label: '안정적인 순방형' },
  { value: 'high_risk_first', label: '고점 높은 1등형' },
  { value: 'easy_beginner', label: '쉬운 초보자형' },
];

const getTierLabel = (value: Tier | null) =>
  TIER_OPTIONS.find((option) => option.value === value)?.label ?? '티어 선택';

const getPlayStyleLabel = (value: PlayStyle | null) =>
  PLAY_STYLE_OPTIONS.find((option) => option.value === value)?.label ??
  '플레이 스타일 선택';

interface DeckRecommendationFormProps {
  inputRef: RefObject<HTMLInputElement | null>;
  query: string;
  tier: Tier | null;
  playStyle: PlayStyle | null;
  isSubmitDisabled: boolean;
  isSubmitting: boolean;
  submitErrorMessage: string | null;
  onQueryChange: (query: string) => void;
  onTierChange: (tier: Tier | null) => void;
  onPlayStyleChange: (playStyle: PlayStyle | null) => void;
  onSubmit: (event: SubmitEvent<HTMLFormElement>) => void;
}

export function DeckRecommendationForm({
  inputRef,
  query,
  tier,
  playStyle,
  isSubmitDisabled,
  isSubmitting,
  submitErrorMessage,
  onQueryChange,
  onTierChange,
  onPlayStyleChange,
  onSubmit,
}: DeckRecommendationFormProps) {
  return (
    <form
      className={`${MAIN_PANEL_CLASS_NAME} mx-auto w-full max-w-3xl overflow-hidden`}
      aria-busy={isSubmitting}
      onSubmit={onSubmit}>
      <div className="flex flex-col gap-3 border-b-4 border-border bg-muted/20 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <MainSectionEyebrow icon={CrosshairIcon}>추천 조건</MainSectionEyebrow>
        <Badge className="h-9 w-fit border-2 border-primary/70 bg-primary/15 font-galmuri11 text-[10px] font-bold text-primary">
          PATCH-ADAPTIVE
        </Badge>
      </div>
      <div className="flex flex-col gap-4 p-5 sm:p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="flex min-w-0 flex-col gap-2">
            <label
              className="font-galmuri11 text-[10px] font-bold text-muted-foreground"
              htmlFor="deck-recommendation-tier">
              티어
            </label>
            <Select<Tier>
              name="tier"
              value={tier}
              disabled={isSubmitting}
              onValueChange={(value) => onTierChange(value)}>
              <SelectTrigger
                id="deck-recommendation-tier"
                type="button"
                className="h-11 w-full border-2 bg-background/80 font-galmuri11 text-sm"
                aria-label="티어 선택">
                <SelectValue
                  className={tier === null ? 'text-muted-foreground' : ''}>
                  {(value) => getTierLabel(value as Tier | null)}
                </SelectValue>
              </SelectTrigger>
              <SelectContent align="start" className="border-2 border-border">
                {TIER_OPTIONS.map((option) => (
                  <SelectItem
                    key={option.value}
                    value={option.value}
                    label={option.label}
                    className="font-galmuri11">
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex min-w-0 flex-col gap-2">
            <label
              className="font-galmuri11 text-[10px] font-bold text-muted-foreground"
              htmlFor="deck-recommendation-play-style">
              플레이 스타일
            </label>
            <Select<PlayStyle>
              name="play_style"
              value={playStyle}
              disabled={isSubmitting}
              onValueChange={(value) => onPlayStyleChange(value)}>
              <SelectTrigger
                id="deck-recommendation-play-style"
                type="button"
                className="h-11 w-full border-2 bg-background/80 font-galmuri11 text-sm"
                aria-label="플레이 스타일 선택">
                <SelectValue
                  className={playStyle === null ? 'text-muted-foreground' : ''}>
                  {(value) => getPlayStyleLabel(value as PlayStyle | null)}
                </SelectValue>
              </SelectTrigger>
              <SelectContent align="start" className="border-2 border-border">
                {PLAY_STYLE_OPTIONS.map((option) => (
                  <SelectItem
                    key={option.value}
                    value={option.value}
                    label={option.label}
                    className="font-galmuri11">
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <label
            className="font-galmuri11 text-[10px] font-bold text-muted-foreground"
            htmlFor="deck-recommendation-query">
            요청
          </label>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Input
              ref={inputRef}
              id="deck-recommendation-query"
              type="search"
              placeholder="어떤 덱으로 플레이하고 싶으신가요?"
              className="h-11 border-2 bg-background/80 font-galmuri11 text-sm"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              disabled={isSubmitting}
              autoComplete="off"
              aria-label="덱 추천을 위한 플레이 스타일 검색어"
              aria-invalid={submitErrorMessage !== null}
              required
            />
            <m.div
              className="w-full sm:w-auto"
              transition={{
                duration: 0.12,
                ease: 'easeOut',
              }}
              whileHover={
                isSubmitDisabled ? undefined : { x: 2, y: 1, scale: 0.98 }
              }
              whileTap={
                isSubmitDisabled ? undefined : { x: 2, y: 3, scale: 0.96 }
              }>
              <Button
                type="submit"
                disabled={isSubmitDisabled || isSubmitting}
                className="h-11 w-full gap-2 border-2 border-primary px-5 font-galmuri11 text-sm font-bold shadow-[4px_4px_0_0_rgb(0_0_0/0.45)] sm:w-auto"
                aria-busy={isSubmitting}
                aria-label="덱 추천 검색하기">
                <GameControllerIcon aria-hidden weight="bold" />
                <span>GURU!</span>
              </Button>
            </m.div>
          </div>
        </div>
        {submitErrorMessage ? (
          <p
            role="alert"
            className="border-2 h-11 inline-flex items-center border-destructive/60 bg-destructive/10 px-3 py-2 text-center text-sm font-bold text-destructive sm:text-left">
            {submitErrorMessage}
          </p>
        ) : null}
      </div>
    </form>
  );
}
