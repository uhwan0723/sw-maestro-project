import { errorContent } from '@/content';

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <p className="text-sm text-muted-foreground">
        {message ?? errorContent.empty ?? '데이터가 없습니다.'}
      </p>
    </div>
  );
}
