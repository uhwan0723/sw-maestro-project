import { API_URL } from '@/api/api-url';
import type {
  PostRecommendRequest,
  PostRecommendResponse,
} from '@/api/post-recommend/type';
import { USE_MOCK } from '@/constants/env';
import { apiClient } from '@/lib/api-client';
import {
  RecommendationResponseSchema,
  RecommendRequestSchema,
} from '@/lib/schema';
import {
  mockDeckPlaystyleResponse,
  mockItemPivotResponse,
  mockRecommendDeckResponse,
} from '@/mocks/recommendation';

const selectMockRecommendation = (question: string) => {
  if (question.includes('운영법')) {
    return mockDeckPlaystyleResponse;
  }

  if (question.includes('곡궁') || question.toUpperCase().includes('BF')) {
    return mockItemPivotResponse;
  }

  return mockRecommendDeckResponse;
};

export const postRecommend = async (
  input: PostRecommendRequest,
): Promise<PostRecommendResponse> => {
  const parsedInput = RecommendRequestSchema.parse(input);

  if (USE_MOCK) {
    const response = RecommendationResponseSchema.parse(
      selectMockRecommendation(parsedInput.question),
    );

    return response;
  }

  let response: unknown;

  try {
    response = await apiClient.post<unknown>(API_URL.RECOMMEND, parsedInput);
  } catch (error) {
    throw error;
  }

  return RecommendationResponseSchema.parse(response);
};
