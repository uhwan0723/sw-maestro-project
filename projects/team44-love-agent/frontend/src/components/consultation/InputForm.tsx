'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { MessageCircle, Sparkles } from 'lucide-react';
import { inputContent } from '@/content';

const MAX_LENGTH = 1000;
const EXAMPLES = [
  '썸남이 연락이 뜸해졌어요. 제가 뭘 잘못한 걸까요?',
  '3년 사귄 남자친구가 요즘 너무 무관심한 것 같아요.',
];

interface InputFormProps {
  onSubmit: (input: string) => void | Promise<void>;
  isLoading?: boolean;
}

export function InputForm({ onSubmit, isLoading }: InputFormProps) {
  const [value, setValue] = useState('');

  return (
    <div className="flex flex-col gap-3 rounded-2xl border bg-white p-6 shadow-sm">
      {/* 카드 헤더 */}
      <div className="flex items-start gap-3">
        <div className="flex size-10 items-center justify-center rounded-full bg-primary/10">
          <MessageCircle className="size-5 text-primary" />
        </div>
        <div>
          <p className="font-semibold">
            {inputContent.title || '연애 고민을 입력해주세요'}
          </p>
          <p className="text-sm text-muted-foreground">
            {inputContent.subtitle || '여러 AI가 다양한 관점에서 분석하고 조언해드릴게요.'}
          </p>
        </div>
      </div>

      {/* Textarea */}
      <div className="flex flex-col gap-1">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value.slice(0, MAX_LENGTH))}
          placeholder={inputContent.placeholder || '연애 고민을 입력해주세요...'}
          className="min-h-32 resize-none text-base"
          disabled={isLoading}
        />
        <p className="self-end text-xs text-muted-foreground">
          {value.length} / {MAX_LENGTH}
        </p>
      </div>

      {/* 하단: 예시 칩 + 버튼 */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="cursor-pointer rounded-full border bg-muted/50 px-4 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted"
              onClick={() => setValue(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
        <Button
          onClick={() => onSubmit(value)}
          disabled={!value.trim() || isLoading}
          className="shrink-0 gap-1.5 px-6 py-5 text-base"
        >
          <Sparkles className="size-4" />
          {inputContent.submitButton || '고민 분석 시작'}
        </Button>
      </div>
    </div>
  );
}
