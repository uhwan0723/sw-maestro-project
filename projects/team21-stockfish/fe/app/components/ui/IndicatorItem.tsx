import { type ReactNode } from "react";
import { cn } from "~/utils/cn";

export interface IndicatorItemProps {
  intent: "success" | "danger";
  label: string;
  value: string;
  icon?: ReactNode;
  className?: string;
}

export function IndicatorItem({ intent, label, value, icon, className }: IndicatorItemProps) {
  const isSuccess = intent === "success";

  return (
    <div
      className={cn(
        "flex items-center justify-between px-3 py-3 rounded-xl border bg-white min-w-72 flex-1",
        isSuccess ? "border-success-600" : "border-danger-600",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "text-base font-medium",
            isSuccess ? "text-success-600" : "text-danger-600",
          )}
        >
          {label}
        </span>
        {icon && (
          <div
            className={cn(
              "size-3.5 flex items-center justify-center",
              isSuccess ? "text-success-600" : "text-danger-600",
            )}
          >
            {icon}
          </div>
        )}
      </div>
      <span className={cn("text-base", isSuccess ? "text-success-600" : "text-danger-600")}>
        {value}
      </span>
    </div>
  );
}
