import { m } from 'motion/react';

export function BrandMark() {
  return (
    <m.div
      className="group flex w-fit cursor-default flex-col gap-3"
      transition={{
        duration: 0.12,
        ease: 'easeOut',
      }}
      whileHover={{ y: -4, scale: 1.02 }}>
      <div className="flex items-center gap-2 font-galmuri11 text-[10px] font-bold text-primary">
        <span className="block size-2 bg-primary shadow-[3px_3px_0_0_rgb(0_0_0/0.45)]" />
        LIVE META CONSOLE
      </div>
      <h1 className="font-galmuri11 text-5xl leading-none font-bold tracking-normal text-foreground sm:text-6xl">
        DECK
        <br />
        <span className="text-primary drop-shadow-[0_0_10px_rgb(241_181_0/0.25)]">
          GURU
        </span>
      </h1>
      <div className="grid h-3 w-full grid-cols-12 border-2 border-border bg-muted/30">
        {Array.from({ length: 12 }).map((_, index) => (
          <span
            aria-hidden
            className={
              index < 7
                ? 'border-r-2 border-background bg-primary'
                : 'border-r-2 border-border/80'
            }
            key={index}
          />
        ))}
      </div>
    </m.div>
  );
}
