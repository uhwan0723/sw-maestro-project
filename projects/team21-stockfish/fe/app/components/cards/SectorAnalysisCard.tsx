import { type ReactNode } from "react";
import { cn } from "~/utils/cn";
import { Icon } from "~/components/ui/Icon";
import { IndicatorItem, type IndicatorItemProps } from "~/components/ui/IndicatorItem";
import { NewsItem, type NewsItemProps } from "~/components/ui/NewsItem";

export interface SectorAnalysisCardProps {
  intent?: "success" | "danger";
  title: string;
  icon?: ReactNode;
  summary: string;
  indicators: (IndicatorItemProps & { id: string | number })[];
  newsList: (NewsItemProps & { id: string | number })[];
  className?: string;
}

export function SectorAnalysisCard({
  intent = "danger",
  title,
  icon,
  summary,
  indicators,
  newsList,
  className,
}: SectorAnalysisCardProps) {
  const isSuccess = intent === "success";

  return (
    <article
      className={cn(
        "flex flex-col border border-neutral-200 rounded-2xl bg-white w-full max-w-2xl overflow-hidden",
        className,
      )}
    >
      {/* Header */}
      <header
        className={cn(
          "flex items-center gap-3 px-5 py-4",
          isSuccess ? "bg-success-50" : "bg-danger-50",
        )}
      >
        {icon && (
          <div
            className={cn(
              "size-5 flex items-center justify-center shrink-0",
              isSuccess ? "text-success-600" : "text-danger-600",
            )}
          >
            {icon}
          </div>
        )}
        <h3
          className={cn(
            "text-base font-normal leading-6",
            isSuccess ? "text-success-600" : "text-danger-600",
          )}
        >
          {title}
        </h3>
      </header>

      {/* Summary */}
      <div className="border-b border-neutral-100 p-5">
        <p className="text-base text-neutral-700 leading-6">{summary}</p>
      </div>

      {/* Indicators */}
      <section className="border-b border-neutral-100 px-5 py-4 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-neutral-500">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
            />
          </Icon>
          <h4 className="text-base text-neutral-500 font-normal leading-6">근거 지표</h4>
        </div>
        <div className="flex flex-wrap gap-3">
          {indicators.map((indicator) => (
            <IndicatorItem key={indicator.id} {...indicator} />
          ))}
        </div>
      </section>

      {/* News List */}
      <section className="px-5 py-4 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-neutral-500">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 002.25 2.25h13.5M6 7.5h3v3H6v-3z"
            />
          </Icon>
          <h4 className="text-base text-neutral-500 font-normal leading-6">근거 기사</h4>
        </div>
        <ul className="flex flex-col gap-2 m-0 p-0 list-none">
          {newsList.map((news) => (
            <li key={news.id}>
              <NewsItem {...news} />
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
