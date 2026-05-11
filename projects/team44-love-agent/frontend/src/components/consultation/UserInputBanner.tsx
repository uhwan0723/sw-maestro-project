import { Pencil } from 'lucide-react';
import { inputContent } from '@/content';

interface UserInputBannerProps {
  userInput: string;
  onEdit?: () => void;
}

export function UserInputBanner({ userInput, onEdit }: UserInputBannerProps) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border bg-white px-4 py-3 shadow-sm">
      <p className="text-xs text-muted-foreground">내 질문</p>
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm">{userInput}</p>
        {onEdit && (
          <button
            onClick={onEdit}
            className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <Pencil className="size-3" />
            {inputContent.editButton}
          </button>
        )}
      </div>
    </div>
  );
}
