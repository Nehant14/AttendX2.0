import { NavLink, useNavigate } from 'react-router-dom';
import { Camera, Users, Table, LogOut } from 'lucide-react';
import { clearAuth, getAuth } from '../api/client';

const adminLinks = [
  { to: '/admin', label: 'Take Attendance', icon: Camera, end: true },
  { to: '/admin/attendance', label: 'Attendance', icon: Table, end: false },
  { to: '/admin/students', label: 'Students', icon: Users, end: false },
];

export const Layout = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate();
  const auth = getAuth();

  const logout = () => {
    clearAuth();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-bold text-gray-900">Attendance</span>
            {auth?.role === 'admin' && (
              <nav className="flex gap-1">
                {adminLinks.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      `inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium ${
                        isActive ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 mr-1.5" />
                    {label}
                  </NavLink>
                ))}
              </nav>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-500">{auth?.name}</span>
            <button
              onClick={logout}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md font-medium text-gray-700 hover:bg-gray-50"
            >
              <LogOut className="w-4 h-4 mr-1.5" />
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
    </div>
  );
};
