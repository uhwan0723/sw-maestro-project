'use client';

import { Button } from '@/components/ui/button';
import { ArrowLeftIcon } from '@phosphor-icons/react';
import { m } from 'motion/react';
import Link from 'next/link';

export function ActionButton({ href, label }: { href: string; label: string }) {
  return (
    <m.div
      className="w-full sm:w-auto"
      transition={{
        duration: 0.12,
        ease: 'easeOut',
      }}
      whileHover={{ x: 2, y: 1, scale: 0.98 }}
      whileTap={{ x: 2, y: 3, scale: 0.96 }}>
      <Button
        type="button"
        nativeButton={false}
        className="h-12 w-full gap-2 px-5 font-galmuri11 text-sm font-bold sm:w-auto"
        aria-label={label}
        render={<Link href={href} />}>
        <ArrowLeftIcon aria-hidden className="size-4" weight="bold" />
        {label}
      </Button>
    </m.div>
  );
}
