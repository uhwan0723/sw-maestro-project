import { Badge } from '@/components/ui/badge';
import { APP_PATH } from '@/constants/app-path';
import type { RecommendationResponse } from '@/lib/schema';

import { ActionButton } from './action-button';

export function ResultHeader({
  recommendation,
}: {
  recommendation: RecommendationResponse;
}) {
  return (
    <header className="flex flex-col gap-5 pt-2 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-col gap-3">
        <Badge
          variant="outline"
          className="h-auto max-w-full border-2 border-primary/70 px-3 py-2 text-[10px] text-primary backdrop-blur">
          REQUEST {recommendation.request_id}
        </Badge>
        <div className="flex flex-col gap-2">
          <h1 className="font-galmuri11 text-2xl font-bold text-foreground sm:text-3xl">
            추천 결과
          </h1>
          <p className="text-sm leading-6 text-muted-foreground sm:text-base">
            메타 요약, 덱별 운영 순서, 좋은 조건과 피해야 할 조건을 한 화면에서
            바로 비교할 수 있게 정리했습니다.
          </p>
        </div>
      </div>

      <ActionButton href={APP_PATH.MAIN} label="다시 추천받기" />
    </header>
  );
}
