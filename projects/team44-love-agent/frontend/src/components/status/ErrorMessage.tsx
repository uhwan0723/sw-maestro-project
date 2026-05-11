import { Button } from '@/components/ui/button';
import { errorContent } from '@/content';

interface ErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-12 text-center">
      <p className="text-sm text-muted-foreground">
        {message ?? errorContent.generic ?? '오류가 발생했습니다.'}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {errorContent.retryButton || '다시 시도'}
        </Button>
      )}
    </div>
  );
}
