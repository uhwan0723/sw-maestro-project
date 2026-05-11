import { type ReactNode } from "react";
import { cn } from "~/utils/cn";

export interface ChatBubbleProps {
  role: "user" | "assistant";
  children: ReactNode;
  className?: string;
}

export function ChatBubble({ role, children, className }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "px-4 py-2 text-sm leading-6 max-w-full wrap-break-word overflow-clip whitespace-pre-wrap",
        isUser
          ? "bg-primary-500 text-white rounded-t-2xl rounded-bl-2xl rounded-br-md"
          : "bg-white text-neutral-800 border border-neutral-200 rounded-t-lg rounded-b-2xl",
        className,
      )}
    >
      {children}
    </div>
  );
}
