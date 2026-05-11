import { type ComponentProps } from "react";
import { cn } from "~/utils/cn";
import { Icon } from "~/components/ui/Icon";

export interface ChatInputProps extends Omit<ComponentProps<"form">, "onSubmit" | "onChange"> {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
  className,
  ...props
}: ChatInputProps) {
  const handleSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (value.trim()) {
      onSubmit(value);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) {
        onSubmit(value);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn("flex items-end gap-2 px-4", className)} {...props}>
      <div className="relative flex-1 h-12">
        <textarea
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-label="메시지 입력"
          placeholder="메시지를 입력하세요..."
          disabled={disabled}
          className="w-full h-12 resize-none rounded-2xl bg-neutral-100 px-4 py-3 text-sm text-neutral-900 outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
          onKeyDown={handleKeyDown}
        />
      </div>
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary-500 text-white transition-colors hover:bg-primary-600 disabled:bg-neutral-300 disabled:text-neutral-500"
        aria-label="보내기"
      >
        <Icon>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
          />
        </Icon>
      </button>
    </form>
  );
}
