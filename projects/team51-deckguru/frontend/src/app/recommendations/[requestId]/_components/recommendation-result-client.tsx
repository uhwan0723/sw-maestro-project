'use client';

import { useRecommendationResultQuery } from '@/api/post-recommend/query';

import { EmptyResultState } from './empty-result-state';
import { RecommendationResultView } from './recommendation-result-view';

interface RecommendationResultClientProps {
  requestId: string;
}

export function RecommendationResultClient({
  requestId,
}: RecommendationResultClientProps) {
  const { data: recommendation } = useRecommendationResultQuery(requestId);

  if (!recommendation) {
    return <EmptyResultState />;
  }

  return <RecommendationResultView recommendation={recommendation} />;
}
