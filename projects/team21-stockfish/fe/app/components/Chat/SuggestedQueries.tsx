import { cn } from "~/utils/cn";
import { Chip } from "~/components/ui/Chip";

export interface SuggestedQueriesProps {
  queries: string[];
  onQueryClick?: (query: string) => void;
  className?: string;
}

export function SuggestedQueries({ queries, onQueryClick, className }: SuggestedQueriesProps) {
  return (
    <nav
      aria-label="추천 검색어"
      className={cn(
        "flex items-center overflow-x-auto gap-2 py-2 px-4",
        "[&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]",
        className,
      )}
    >
      {queries.map((query) => (
        <Chip key={query} onClick={() => onQueryClick?.(query)} className="text-sm">
          {query}
        </Chip>
      ))}
    </nav>
  );
}
