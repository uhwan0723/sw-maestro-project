import { type ReactNode } from "react";
import { cn } from "~/utils/cn";

export interface ExplanationBoxProps {
  definition: string | ReactNode;
  example?: string | ReactNode;
  className?: string;
}

export function ExplanationBox({ definition, example, className }: ExplanationBoxProps) {
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="bg-neutral-50 px-4 py-3 rounded-xl text-base text-neutral-700 leading-6 whitespace-pre-wrap">
        {definition}
      </div>

      {example && (
        <div className="flex items-start gap-2 text-base text-neutral-600 leading-6">
          <div className="pt-1 select-none shrink-0" aria-hidden="true">
            💡
          </div>
          <div>{example}</div>
        </div>
      )}
    </div>
  );
}
