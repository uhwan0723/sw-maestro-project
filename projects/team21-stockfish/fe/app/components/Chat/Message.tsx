import { type ReactNode } from "react";
import { cn } from "~/utils/cn";

export interface MessageProps {
  role: "user" | "assistant";
  children: ReactNode;
  className?: string;
}

export function Message({ role, children, className }: MessageProps) {
  const isUser = role === "user";

  return (
    <article
      className={cn("flex w-full mb-6", isUser ? "justify-end" : "justify-start", className)}
    >
      <div
        className={cn(
          "max-w-full md:max-w-[85%] flex flex-col gap-2",
          isUser ? "items-end" : "items-start",
        )}
      >
        {children}
      </div>
    </article>
  );
}
