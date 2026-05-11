'use client';

import { type PropsWithChildren, useState } from 'react';

import { makeQueryClient } from '@/lib/query-client';
import { QueryClientProvider } from '@tanstack/react-query';

export function QueryProvider({ children }: PropsWithChildren) {
  const [queryClient] = useState(() => makeQueryClient());

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
