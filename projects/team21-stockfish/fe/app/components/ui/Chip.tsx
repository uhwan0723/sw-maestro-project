import { type ComponentProps } from "react";
import { cn } from "~/utils/cn";

interface ChipProps extends ComponentProps<"button"> {
  active?: boolean;
}

export function Chip({ active, className, children, ...props }: ChipProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full px-4 py-1.5 min-h-8 text-base font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
        active
          ? "bg-primary-500 text-white"
          : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
