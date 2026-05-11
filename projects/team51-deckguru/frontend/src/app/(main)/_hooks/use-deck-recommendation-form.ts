import { type SubmitEvent, useRef, useState } from 'react';

import { usePostRecommendMutation } from '@/api/post-recommend/mutation';
import { APP_PATH } from '@/constants/app-path';
import type { PlayStyle, Tier } from '@/lib/schema';
import { useRouter } from 'next/navigation';

const DEFAULT_SUBMIT_ERROR_MESSAGE =
  '추천 요청 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';

const getSubmitErrorMessage = (error: unknown) => {
  if (error instanceof Error) {
    return error.message;
  }

  return DEFAULT_SUBMIT_ERROR_MESSAGE;
};

export function useDeckRecommendationForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [tier, setTier] = useState<Tier | null>(null);
  const [playStyle, setPlayStyle] = useState<PlayStyle | null>(null);
  const [isNavigatingToResult, setIsNavigatingToResult] = useState(false);
  const recommendationMutation = usePostRecommendMutation({
    onSuccess: (response) => {
      setIsNavigatingToResult(true);
      router.push(APP_PATH.RECOMMENDATION_RESULT(response.request_id));
    },
    onError: () => {
      setIsNavigatingToResult(false);
    },
  });
  const isSubmitting = recommendationMutation.isPending || isNavigatingToResult;
  const isSubmitDisabled =
    query.trim().length === 0 ||
    tier === null ||
    playStyle === null ||
    isSubmitting;
  const submitErrorMessage = recommendationMutation.isError
    ? getSubmitErrorMessage(recommendationMutation.error)
    : null;

  const handleExampleQuestionClick = (question: string) => {
    setQuery(question);

    if (!inputRef.current) {
      return;
    }

    inputRef.current.focus();
  };

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    const trimmedQuery = query.trim();

    if (!trimmedQuery || tier === null || playStyle === null || isSubmitting) {
      return;
    }

    recommendationMutation.mutate({
      question: trimmedQuery,
      tier,
      play_style: playStyle,
    });
  };

  return {
    inputRef,
    query,
    tier,
    playStyle,
    isSubmitDisabled,
    isSubmitting,
    submitErrorMessage,
    setQuery,
    setTier,
    setPlayStyle,
    handleExampleQuestionClick,
    handleSubmit,
  };
}
