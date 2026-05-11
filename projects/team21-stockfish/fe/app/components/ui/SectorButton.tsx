import type { ComponentProps, ReactNode } from "react";
import { cn } from "~/utils/cn";

export interface SectorButtonProps extends ComponentProps<"button"> {
  icon: ReactNode;
  label: string;
}

export function SectorButton({ icon, label, className, ...props }: SectorButtonProps) {
  return (
    <button
      className={cn(
        "flex flex-col items-center justify-center gap-1 w-15 h-15 rounded-xl",
        "bg-neutral-50 border border-neutral-300 transition-colors",
        "hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-primary-500 outline-none",
        className,
      )}
      {...props}
    >
      <div className="size-6 shrink-0 flex items-center justify-center text-neutral-500">
        {icon}
      </div>
      <span className="text-xs text-neutral-500 font-normal">{label}</span>
    </button>
  );
}
