import { recommendationResultQueryKey } from '@/api/post-recommend/query-key';
import type { PostRecommendResponse } from '@/api/post-recommend/type';
import type { OmittedQueryOptions } from '@/lib/query-client';
import { useQuery } from '@tanstack/react-query';

const getCachedRecommendationResult = async (): Promise<PostRecommendResponse> => {
  throw new Error('recommendation_result_not_found');
};

export const useRecommendationResultQuery = (
  requestId: string,
  options?: OmittedQueryOptions<PostRecommendResponse>,
) => {
  return useQuery({
    queryKey: recommendationResultQueryKey(requestId),
    queryFn: getCachedRecommendationResult,
    ...options,
    enabled: false,
  });
};
