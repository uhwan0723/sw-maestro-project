import { postRecommend } from '@/api/post-recommend/post';
import { recommendationResultQueryKey } from '@/api/post-recommend/query-key';
import type {
  PostRecommendRequest,
  PostRecommendResponse,
} from '@/api/post-recommend/type';
import type { OmittedMutationOptions } from '@/lib/query-client';
import { useMutation, useQueryClient } from '@tanstack/react-query';

export const postRecommendMutationKey = () => ['recommend'] as const;

export const usePostRecommendMutation = (
  options?: OmittedMutationOptions<
    PostRecommendResponse,
    Error,
    PostRecommendRequest
  >,
) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...mutationOptions } = options ?? {};

  return useMutation({
    mutationKey: postRecommendMutationKey(),
    mutationFn: postRecommend,
    ...mutationOptions,
    onSuccess: (data, variables, onMutateResult, context) => {
      queryClient.setQueryData(
        recommendationResultQueryKey(data.request_id),
        data,
      );
      onSuccess?.(data, variables, onMutateResult, context);
    },
  });
};
