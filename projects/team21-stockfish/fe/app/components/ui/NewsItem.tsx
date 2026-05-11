import { cn } from "~/utils/cn";
import { StatusDot } from "./StatusDot";

export interface NewsItemProps {
  intent?: "success" | "danger" | "neutral";
  title: string;
  source: string;
  url?: string;
  className?: string;
}

export function NewsItem({ intent = "neutral", title, source, url, className }: NewsItemProps) {
  const Component = url ? "a" : "div";
  const linkProps = url ? { href: url, target: "_blank", rel: "noopener noreferrer" } : {};

  return (
    <Component
      {...linkProps}
      className={cn(
        "flex items-start gap-3 p-4 bg-neutral-50 rounded-xl w-full",
        url &&
          "hover:bg-neutral-100 transition-colors focus-visible:ring-2 focus-visible:ring-primary-500 outline-none",
        className,
      )}
    >
      <div className="pt-2 shrink-0">
        <StatusDot intent={intent} />
      </div>
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <h4 className="text-base text-neutral-800 font-normal truncate">{title}</h4>
        <span className="text-base text-neutral-400 font-normal truncate">{source}</span>
      </div>
    </Component>
  );
}
