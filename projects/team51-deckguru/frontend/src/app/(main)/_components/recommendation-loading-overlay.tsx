'use client';

import { createPortal } from 'react-dom';

import { m } from 'motion/react';

const loadingSteps = [
  '메타 스냅샷 확인',
  '덱 시너지 계산',
  '추천 결과 정리',
] as const;

export function RecommendationLoadingOverlay() {
  const portalRoot = typeof document === 'undefined' ? null : document.body;

  if (!portalRoot) {
    return null;
  }

  return createPortal(
    <m.div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-busy="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/45 px-4 py-[max(1rem,env(safe-area-inset-top))] text-foreground backdrop-blur-md"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}>
      <m.div
        className="w-full max-w-lg border-4 border-border bg-background/95 shadow-[6px_6px_0_0_rgb(0_0_0/0.5)] backdrop-blur"
        initial={{ opacity: 0, y: -10, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}>
        <div className="flex items-center gap-6 border-b-4 border-border bg-primary/15 p-4 sm:p-5">
          <div
            className="relative flex size-11 shrink-0 items-center justify-center"
            aria-hidden="true">
            <span className="absolute inset-0 animate-spin border-4 border-primary/25 border-t-primary motion-reduce:animate-none" />
          </div>
          <div className="min-w-0">
            <p className="font-galmuri11 text-[10px] font-bold text-primary">
              GURU ENGINE ONLINE
            </p>
            <p className="mt-1 text-base font-bold sm:text-lg">
              AI가 추천 덱을 분석하고 있습니다
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-4 p-4 sm:p-5">
          <p className="text-sm leading-6 text-muted-foreground">
            최신 패치와 요청 조건을 바탕으로 후보 덱을 좁히는 중입니다.
          </p>

          <div className="grid grid-cols-12 gap-1" aria-hidden="true">
            {Array.from({ length: 12 }, (_, index) => (
              <span
                key={index}
                className="h-2 animate-pulse border border-primary/50 bg-primary/25 motion-reduce:animate-none"
                style={{ animationDelay: `${index * 80}ms` }}
              />
            ))}
          </div>

          <ul className="grid gap-2">
            {loadingSteps.map((step) => (
              <li
                key={step}
                className="flex items-center gap-2 border-2 border-border bg-muted/20 px-3 py-2 text-xs font-bold text-muted-foreground">
                <span
                  className="size-2 shrink-0 animate-pulse bg-primary motion-reduce:animate-none"
                  aria-hidden="true"
                />
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      </m.div>
    </m.div>,
    portalRoot,
  );
}
