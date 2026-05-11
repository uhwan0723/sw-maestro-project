import { cn } from "~/utils/cn";

export interface StatusDotProps {
  intent?: "success" | "danger" | "neutral" | "primary";
  className?: string;
}

export function StatusDot({ intent = "neutral", className }: StatusDotProps) {
  return (
    <span
      className={cn(
        "inline-block rounded-full size-2 shrink-0",
        {
          "bg-success-500": intent === "success",
          "bg-danger-500": intent === "danger",
          "bg-primary-500": intent === "primary",
          "bg-neutral-400": intent === "neutral",
        },
        className,
      )}
      aria-hidden="true"
    />
  );
}
