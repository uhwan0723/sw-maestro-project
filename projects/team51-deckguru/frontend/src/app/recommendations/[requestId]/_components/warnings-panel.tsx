import { formatWarningMessage } from '@/lib/warnings';
import { WarningIcon } from '@phosphor-icons/react';

import { SectionEyebrow } from './recommendation-result-shared';

export function WarningsPanel({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) {
    return null;
  }

  const warningMessages = warnings.map((warning) =>
    formatWarningMessage(warning),
  );

  return (
    <section
      className="border-4 border-destructive/70 bg-destructive/10 p-5 shadow-[8px_8px_0_0_rgb(0_0_0/0.45)]"
      aria-labelledby="recommendation-warnings-title">
      <SectionEyebrow icon={WarningIcon}>주의</SectionEyebrow>
      <h2
        id="recommendation-warnings-title"
        className="mt-3 font-galmuri11 text-base font-bold text-foreground">
        확인이 필요한 안내
      </h2>
      <ul className="mt-3 flex flex-col gap-2">
        {warningMessages.map((warning, index) => (
          <li
            className="border-l-2 border-destructive/50 pl-3 text-sm leading-6 text-foreground/90"
            key={`${warning.title}-${index}`}>
            <p className="font-semibold text-foreground">{warning.title}</p>
            <p>{warning.description}</p>
            {warning.detail ? (
              <p className="mt-1 text-xs break-all text-muted-foreground">
                {warning.detail}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
