import type { ComponentType, ReactNode } from 'react';

export type IconComponent = ComponentType<{
  'aria-hidden'?: boolean;
  className?: string;
  weight?: 'bold' | 'duotone' | 'fill' | 'regular';
}>;

export const PANEL_CLASS_NAME =
  'border-4 border-border bg-background/95 shadow-[8px_8px_0_0_rgb(0_0_0/0.45)] backdrop-blur';

export function SectionEyebrow({
  children,
  icon: Icon,
}: {
  children: ReactNode;
  icon: IconComponent;
}) {
  return (
    <p className="flex items-center gap-1.5 font-galmuri11 text-[10px] font-bold text-primary">
      <Icon aria-hidden className="size-3.5" weight="bold" />
      <span>{children}</span>
    </p>
  );
}
