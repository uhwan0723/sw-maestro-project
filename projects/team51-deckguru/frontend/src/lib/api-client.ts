import { ApiErrorResponseSchema } from '@/lib/schema';

const API_BASE_URL =
  typeof window === 'undefined'
    ? process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL
    : process.env.NEXT_PUBLIC_API_BASE_URL;

const TIMEOUT_MS = 45 * 1000;

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const normalizeEndpoint = (endpoint: string) =>
  endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

const buildRequestUrl = (endpoint: string) =>
  `${API_BASE_URL ? trimTrailingSlash(API_BASE_URL) : ''}${normalizeEndpoint(endpoint)}`;

const parseResponseBody = <T>(text: string): T | null => {
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
};

const getErrorMessage = (data: unknown) => {
  const parsed = ApiErrorResponseSchema.safeParse(data);

  if (parsed.success) {
    return parsed.data.error.message;
  }

  return '요청 처리 중 오류가 발생했습니다.';
};

const request = async <T>(
  endpoint: string,
  options: RequestInit,
): Promise<T> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(buildRequestUrl(endpoint), {
      headers: { 'Content-Type': 'application/json' },
      ...options,
      signal: controller.signal,
    });

    const text = await res.text();
    const data = parseResponseBody<T>(text);

    if (!res.ok) {
      throw new Error(getErrorMessage(data));
    }

    return data as T;
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('요청 시간이 초과되었습니다.');
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
};

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'GET', ...options }),
  post: <T>(endpoint: string, body: unknown, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
      ...options,
    }),
};
