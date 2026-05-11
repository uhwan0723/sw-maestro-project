import { type ReactNode } from "react";
import { cn } from "~/utils/cn";
import { Icon } from "~/components/ui/Icon";
import { ExplanationBox } from "~/components/ui/ExplanationBox";
import { Chip } from "~/components/ui/Chip";

export interface TermExplanationCardProps {
  term: string;
  brief: string;
  definition: string | ReactNode;
  example?: string | ReactNode;
  relatedTerms?: string[];
  onRelatedTermClick?: (term: string) => void;
  className?: string;
}

export function TermExplanationCard({
  term,
  brief,
  definition,
  example,
  relatedTerms = [],
  onRelatedTermClick,
  className,
}: TermExplanationCardProps) {
  return (
    <article
      className={cn(
        "flex flex-col border border-neutral-200 rounded-2xl bg-white w-full max-w-2xl overflow-hidden",
        className,
      )}
    >
      {/* Header */}
      <header className="flex items-center gap-2 px-5 py-3 bg-primary-50">
        <Icon className="size-4 text-primary-600">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
          />
        </Icon>
        <span className="text-base font-normal leading-6 text-primary-600">용어 풀이</span>
      </header>

      <div className="p-5 flex flex-col gap-4">
        {/* Title & Brief */}
        <div className="flex flex-col gap-1">
          <h3 className="text-base font-bold leading-6 text-neutral-900">{term}</h3>
          <p className="text-base font-normal leading-6 text-neutral-600">{brief}</p>
        </div>

        {/* Explanation Box */}
        <ExplanationBox definition={definition} example={example} />

        {/* Related Terms */}
        {relatedTerms.length > 0 && (
          <div className="flex flex-col gap-2 pt-3 border-t border-neutral-100">
            <span className="text-base text-neutral-400 font-normal leading-6">관련 용어</span>
            <div className="flex flex-wrap gap-2">
              {relatedTerms.map((relatedTerm) => (
                <Chip key={relatedTerm} onClick={() => onRelatedTermClick?.(relatedTerm)}>
                  {relatedTerm}
                </Chip>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
