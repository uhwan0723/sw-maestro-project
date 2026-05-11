import { type SVGProps } from "react";
import { cn } from "~/utils/cn";

export interface IconProps extends SVGProps<SVGSVGElement> {
  className?: string;
}

export function Icon({ children, className, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className={cn("w-6 h-6 shrink-0", className)}
      {...props}
    >
      {children}
    </svg>
  );
}
