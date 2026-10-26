import { vi } from 'vitest';

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Install a fake fetch backed by a route table keyed by "METHOD /path" (query string ignored). */
export function mockFetch(routes: Record<string, Handler>) {
  const calls: { method: string; url: string; init?: RequestInit }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = (init?.method || 'GET').toUpperCase();
    calls.push({ method, url, init });
    const path = url.split('?')[0];
    const handler = routes[`${method} ${path}`];
    if (!handler) return json({ detail: `no mock for ${method} ${path}`, code: 'NOT_FOUND' }, 404);
    return handler(url, init);
  });
  vi.stubGlobal('fetch', fn);
  return { fn, calls };
}

export function headerOf(init: RequestInit | undefined, name: string): string | null {
  return new Headers(init?.headers || {}).get(name);
}
