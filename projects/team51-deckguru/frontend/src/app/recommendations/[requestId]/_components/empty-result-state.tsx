import { APP_PATH } from '@/constants/app-path';
import { WarningIcon } from '@phosphor-icons/react';

import { ActionButton } from './action-button';

export function EmptyResultState() {
  return (
    <main className="pixel-background relative isolate flex min-h-dvh w-full flex-col items-center justify-center overflow-hidden px-5 py-10 text-center">
      <section className="relative z-10 flex w-full max-w-xl flex-col items-center gap-6">
        <div className="grid size-14 place-items-center border-4 border-primary bg-background/95 text-primary shadow-[6px_6px_0_0_rgb(0_0_0/0.45)]">
          <WarningIcon aria-hidden className="size-7" weight="bold" />
        </div>
        <div className="flex flex-col gap-3">
          <h1 className="font-galmuri11 text-xl font-bold text-primary sm:text-2xl">
            결과를 찾을 수 없습니다
          </h1>
          <div className="flex flex-col text-center text-sm leading-relaxed text-muted-foreground">
            <p>
              새로고침했거나 결과 주소로 바로 접근하면
              <br className="block sm:hidden" /> 임시 추천 결과가 사라집니다.
            </p>
            <p>메인에서 다시 추천을 요청해 주세요.</p>
          </div>
        </div>
        <ActionButton href={APP_PATH.MAIN} label="메인으로 돌아가기" />
      </section>
    </main>
  );
}
