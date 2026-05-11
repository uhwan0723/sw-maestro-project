import { RecommendationResultClient } from '@/app/recommendations/[requestId]/_components/recommendation-result-client';

interface RecommendationResultPageProps {
  params: Promise<{
    requestId: string;
  }>;
}

export default async function RecommendationResultPage({
  params,
}: RecommendationResultPageProps) {
  const { requestId } = await params;

  return <RecommendationResultClient requestId={requestId} />;
}
