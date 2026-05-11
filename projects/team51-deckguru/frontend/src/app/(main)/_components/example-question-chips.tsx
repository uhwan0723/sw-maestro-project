import { Button } from '@/components/ui/button';
import { SparkleIcon } from '@phosphor-icons/react';
import { m } from 'motion/react';

import { MainSectionEyebrow } from './main-page-shared';

interface ExampleQuestionChipsProps {
  questions: string[];
  isDisabled?: boolean;
  onQuestionClick: (question: string) => void;
}

export function ExampleQuestionChips({
  questions,
  isDisabled = false,
  onQuestionClick,
}: ExampleQuestionChipsProps) {
  return (
    <div className="flex w-full max-w-3xl flex-col gap-3">
      <MainSectionEyebrow icon={SparkleIcon}>요청 예시</MainSectionEyebrow>
      <div className="flex flex-wrap items-center gap-2">
        {questions.map((question, index) => (
          <m.div
            key={question}
            initial={{ opacity: 0, y: 6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
              delay: index * 0.06,
              duration: 0.24,
              ease: 'easeOut',
            }}
            whileHover={
              isDisabled
                ? undefined
                : {
                    x: 2,
                    y: 1,
                    scale: 0.96,
                    transition: { delay: 0, duration: 0.12, ease: 'easeOut' },
                  }
            }
            whileTap={
              isDisabled
                ? undefined
                : {
                    x: 2,
                    y: 3,
                    scale: 0.96,
                    transition: { delay: 0, duration: 0.12, ease: 'easeOut' },
                  }
            }>
            <Button
              type="button"
              variant="outline"
              size="lg"
              disabled={isDisabled}
              onClick={() => onQuestionClick(question)}
              className="h-11 max-w-full border-2 bg-background/80 px-3 py-2 text-left text-xs leading-5 whitespace-normal shadow-[3px_3px_0_0_rgb(0_0_0/0.35)] hover:border-primary/70 hover:bg-primary/10 hover:text-primary">
              {question}
            </Button>
          </m.div>
        ))}
      </div>
    </div>
  );
}
