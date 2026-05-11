import { type ReactNode } from "react";
import { cn } from "~/utils/cn";
import { SectorButton } from "~/components/ui/SectorButton";

export interface Sector {
  id: string;
  label: string;
  icon: ReactNode;
}

export interface SectorQuickNavProps {
  sectors: Sector[];
  onSectorClick?: (id: string) => void;
  className?: string;
}

export function SectorQuickNav({ sectors, onSectorClick, className }: SectorQuickNavProps) {
  return (
    <nav aria-label="빠른 섹터 분석" className={cn("flex flex-col", className)}>
      <h2 className="text-base text-neutral-500 font-normal px-5">빠른 섹터 분석</h2>
      <div
        className={cn(
          "flex items-center overflow-x-auto gap-2 py-2 px-4",
          "[&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]",
        )}
      >
        {sectors.map((sector) => (
          <div key={sector.id} className="snap-start shrink-0">
            <SectorButton
              label={sector.label}
              icon={sector.icon}
              onClick={() => onSectorClick?.(sector.id)}
            />
          </div>
        ))}
      </div>
    </nav>
  );
}
