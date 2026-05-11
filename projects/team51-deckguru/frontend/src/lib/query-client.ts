import {
  QueryClient,
  type UseMutationOptions,
  type UseQueryOptions,
  type UseSuspenseQueryOptions,
} from '@tanstack/react-query';

const DEFAULT_QUERY_GC_TIME = 1000 * 60 * 5;

const DEFAULT_STALE_TIME = 1000 * 60;

export const makeQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: DEFAULT_QUERY_GC_TIME,
        staleTime: DEFAULT_STALE_TIME,
        refetchOnWindowFocus: false,
        throwOnError: false,
      },
      mutations: {
        throwOnError: false,
      },
    },
  });
};

export type OmittedQueryOptions<
  TQueryFnData = unknown,
  TError = Error,
  TData = TQueryFnData,
> = Omit<UseQueryOptions<TQueryFnData, TError, TData>, 'queryKey' | 'queryFn'>;

export type OmittedSuspenseQueryOptions<
  TQueryFnData = unknown,
  TError = Error,
  TData = TQueryFnData,
> = Omit<
  UseSuspenseQueryOptions<TQueryFnData, TError, TData>,
  'queryKey' | 'queryFn'
>;

export type OmittedMutationOptions<
  TData = unknown,
  TError = Error,
  TVariables = void,
  TContext = unknown,
> = Omit<
  UseMutationOptions<TData, TError, TVariables, TContext>,
  'mutationKey' | 'mutationFn'
>;
