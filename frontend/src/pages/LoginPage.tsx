import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setAuth } from '../api/client';
import { LoginResponse } from '../api/types';

export const LoginPage = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      setAuth({ token: res.access_token, role: res.role, name: res.name });
      navigate(res.role === 'admin' ? '/admin' : '/student', { replace: true });
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const input =
    'w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600';

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="max-w-sm w-full bg-white rounded-2xl shadow-lg border border-gray-100 p-8 space-y-4">
        <div className="text-center mb-2">
          <h1 className="text-2xl font-bold text-gray-900">Attendance</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in as admin or student</p>
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">{error}</div>}

        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase mb-1.5">Email or Roll No</label>
          <input required value={username} onChange={(e) => setUsername(e.target.value)} className={input} />
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase mb-1.5">Password</label>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>
    </div>
  );
};
