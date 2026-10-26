export const TOKEN_KEY = 'attendance_token';

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function authHeaders(headers: Headers): Headers {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return headers;
}

function handleUnauthorized(endpoint: string): void {
  // A wrong password on the login form must not wipe state or redirect.
  if (endpoint.includes('/api/auth/login')) return;
  localStorage.removeItem(TOKEN_KEY);
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login';
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let detail = `Request failed (${response.status})`;
  let code: string | undefined;
  try {
    const text = await response.text();
    try {
      const json = JSON.parse(text);
      if (typeof json.detail === 'string') detail = json.detail;
      else if (json.detail) detail = JSON.stringify(json.detail);
      code = json.code;
    } catch {
      if (text) detail = text.slice(0, 300);
    }
  } catch {
    /* ignore */
  }
  return new ApiError(response.status, detail, code);
}

async function doFetch(endpoint: string, options: RequestInit): Promise<Response> {
  try {
    return await fetch(endpoint, options);
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check your connection and try again.', 'NETWORK');
  }
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = authHeaders(new Headers(options.headers || {}));
  // Do not set Content-Type for FormData (the browser adds the multipart boundary)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await doFetch(endpoint, { ...options, headers });

  if (response.status === 401) {
    const err = await errorFromResponse(response);
    handleUnauthorized(endpoint);
    throw err;
  }
  if (!response.ok) throw await errorFromResponse(response);
  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

/** Fetch a protected binary resource (image / CSV) with the JWT attached. */
export async function apiBlob(endpoint: string): Promise<Blob> {
  const response = await doFetch(endpoint, { headers: authHeaders(new Headers()) });
  if (response.status === 401) {
    const err = await errorFromResponse(response);
    handleUnauthorized(endpoint);
    throw err;
  }
  if (!response.ok) throw await errorFromResponse(response);
  return response.blob();
}

/** Download a protected file (e.g. CSV). Plain <a href> links cannot send the JWT. */
export async function downloadFile(endpoint: string, fallbackName: string): Promise<void> {
  const response = await doFetch(endpoint, { headers: authHeaders(new Headers()) });
  if (response.status === 401) {
    const err = await errorFromResponse(response);
    handleUnauthorized(endpoint);
    throw err;
  }
  if (!response.ok) throw await errorFromResponse(response);

  let filename = fallbackName;
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  if (match) filename = match[1];

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
