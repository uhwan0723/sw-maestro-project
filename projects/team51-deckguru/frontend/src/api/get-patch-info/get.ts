import { API_URL } from '@/api/api-url';
import type { GetPatchInfoResponse } from '@/api/get-patch-info/type';
import { USE_MOCK } from '@/constants/env';
import { apiClient } from '@/lib/api-client';
import { PatchInfoSchema } from '@/lib/schema';
import { mockPatchInfo } from '@/mocks/patch-info';

export const getPatchInfo = async (): Promise<GetPatchInfoResponse> => {
  if (USE_MOCK) {
    return PatchInfoSchema.parse(mockPatchInfo);
  }

  const response = await apiClient.get<unknown>(API_URL.PATCH_INFO);

  return PatchInfoSchema.parse(response);
};
