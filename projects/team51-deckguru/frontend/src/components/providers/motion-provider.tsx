'use client';

import { type PropsWithChildren } from 'react';

import { LazyMotion } from 'motion/react';

const loadFeatures = () => import('motion/react').then((m) => m.domAnimation);

export function MotionProvider({ children }: PropsWithChildren) {
  return (
    <LazyMotion strict features={loadFeatures}>
      {children}
    </LazyMotion>
  );
}
