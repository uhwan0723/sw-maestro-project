import type { ComponentType, ReactNode } from 'react';

export type MainIconComponent = ComponentType<{
  'aria-hidden'?: boolean;
  className?: string;
  weight?: 'bold' | 'duotone' | 'fill' | 'regular';
}>;

export const MAIN_PANEL_CLASS_NAME =
  'border-4 border-border bg-background/95 shadow-[4px_4px_0_0_rgb(0_0_0/0.45)] backdrop-blur sm:shadow-[8px_8px_0_0_rgb(0_0_0/0.45)]';

export function MainSectionEyebrow({
  children,
  icon: Icon,
}: {
  children: ReactNode;
  icon: MainIconComponent;
}) {
  return (
    <p className="flex items-center gap-1.5 font-galmuri11 text-[10px] font-bold text-primary">
      <Icon aria-hidden className="size-3.5" weight="bold" />
      <span>{children}</span>
    </p>
  );
}
