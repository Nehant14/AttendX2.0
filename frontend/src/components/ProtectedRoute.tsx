import React, { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { TOKEN_KEY } from '../api/client';

type AuthState = 'checking' | 'ok' | 'denied' | 'offline';

/**
 * Asks the backend who we are. With AUTH_ENABLED=false /api/auth/me succeeds without a
 * token, so the login page is skipped; otherwise a missing/expired token goes to /login.
 */
export const ProtectedRoute: React.FC = () => {
  const [state, setState] = useState<AuthState>('checking');

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    fetch('/api/auth/me', { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => {
        if (res.ok) setState('ok');
        else {
          if (res.status === 401) localStorage.removeItem(TOKEN_KEY);
          setState('denied');
        }
      })
      .catch(() => setState('offline'));
  }, []);

  if (state === 'checking') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }
  if (state === 'offline') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
        <div className="max-w-sm text-center bg-white border border-red-200 rounded-xl p-6 shadow-sm">
          <p className="font-semibold text-red-700">Cannot reach the server</p>
          <p className="text-sm text-gray-500 mt-1">Make sure the backend is running, then reload.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  if (state === 'denied') return <Navigate to="/login" replace />;
  return <Outlet />;
};
