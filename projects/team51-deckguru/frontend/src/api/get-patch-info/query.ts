import { getPatchInfo } from '@/api/get-patch-info/get';
import { patchInfoQueryKey } from '@/api/get-patch-info/query-key';
import type { GetPatchInfoResponse } from '@/api/get-patch-info/type';
import type {
  OmittedQueryOptions,
  OmittedSuspenseQueryOptions,
} from '@/lib/query-client';
import { useQuery, useSuspenseQuery } from '@tanstack/react-query';

export const usePatchInfoQuery = (
  options?: OmittedQueryOptions<GetPatchInfoResponse>,
) => {
  return useQuery({
    queryKey: patchInfoQueryKey(),
    queryFn: getPatchInfo,
    ...options,
  });
};

export const usePatchInfoSuspenseQuery = (
  options?: OmittedSuspenseQueryOptions<GetPatchInfoResponse>,
) => {
  return useSuspenseQuery({
    queryKey: patchInfoQueryKey(),
    queryFn: getPatchInfo,
    ...options,
  });
};
