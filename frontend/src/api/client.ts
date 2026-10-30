import { Role } from './types';

const KEY = 'auth';

export interface Auth {
  token: string;
  role: Role;
  name: string;
}

export const getAuth = (): Auth | null => {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null');
  } catch {
    return null;
  }
};
export const setAuth = (a: Auth) => localStorage.setItem(KEY, JSON.stringify(a));
export const clearAuth = () => localStorage.removeItem(KEY);

/** fetch + JWT header + JSON; throws Error(message) on failure. */
export async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const auth = getAuth();
  if (auth) headers.set('Authorization', `Bearer ${auth.token}`);
  if (typeof options.body === 'string') headers.set('Content-Type', 'application/json');

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && !url.includes('/auth/login')) {
    clearAuth();
    window.location.href = '/login';
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === 'string') msg = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}
