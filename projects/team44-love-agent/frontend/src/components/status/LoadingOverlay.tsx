import { Skeleton } from '@/components/ui/skeleton';
import { statusContent } from '@/content';

interface LoadingOverlayProps {
  phase?: string; // ConsultationStatus 값
}

export function LoadingOverlay({ phase = 'analyzing' }: LoadingOverlayProps) {
  const content = statusContent[phase];
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16">
      <div className="flex flex-col items-center gap-3">
        <Skeleton className="size-16 rounded-full" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="flex flex-col items-center gap-1 animate-pulse">
        <p className="text-sm font-medium text-foreground">{content?.short ?? '분석 중'}</p>
        {content?.description && (
          <p className="text-xs text-muted-foreground">{content.description}</p>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-40 rounded-lg" />
        ))}
      </div>
    </div>
  );
}
