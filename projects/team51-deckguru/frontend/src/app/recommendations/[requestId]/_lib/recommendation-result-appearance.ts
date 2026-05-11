import type { Confidence, Difficulty } from '@/lib/schema';

export const CONFIDENCE_CONFIG: Record<
  Confidence,
  { className: string; label: string }
> = {
  high: {
    label: '높음',
    className: 'border-emerald-300/70 bg-emerald-300/15 text-emerald-100',
  },
  medium: {
    label: '보통',
    className: 'border-primary/70 bg-primary/15 text-primary',
  },
  low: {
    label: '낮음',
    className: 'border-rose-300/70 bg-rose-300/15 text-rose-100',
  },
};

export const DIFFICULTY_CONFIG: Record<
  Difficulty,
  { blocks: number; className: string; label: string; summary: string }
> = {
  easy: {
    label: '쉬움',
    blocks: 1,
    summary: '순서대로 따라가기 좋음',
    className: 'border-emerald-300/70 bg-emerald-300/15 text-emerald-100',
  },
  medium: {
    label: '보통',
    blocks: 2,
    summary: '중반 판단이 중요함',
    className: 'border-primary/70 bg-primary/15 text-primary',
  },
  hard: {
    label: '어려움',
    blocks: 3,
    summary: '경제와 피벗 숙련도 필요',
    className: 'border-rose-300/70 bg-rose-300/15 text-rose-100',
  },
};
