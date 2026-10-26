import React from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Camera, Users, BookOpen, Clock, LogOut } from 'lucide-react';
import { TOKEN_KEY } from '../api/client';

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    navigate('/login');
  };

  const navItems = [
    { name: 'Take Attendance', path: '/', icon: Camera },
    { name: 'Students', path: '/students', icon: Users },
    { name: 'Courses', path: '/courses', icon: BookOpen },
    { name: 'History', path: '/history', icon: Clock },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="flex items-center gap-2">
                <div className="bg-indigo-600 text-white p-2 rounded-lg font-bold text-lg leading-none">
                  AX
                </div>
                <span className="font-bold text-xl text-gray-900 tracking-tight">AttendX 2.0</span>
              </Link>
              <nav className="hidden md:ml-8 md:flex md:space-x-4">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === '/'}
                      className={({ isActive }) =>
                        `inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                          isActive
                            ? 'bg-indigo-50 text-indigo-700'
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                        }`
                      }
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {item.name}
                    </NavLink>
                  );
                })}
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={handleLogout}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4 mr-1.5 text-gray-500" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile navigation (the top nav is hidden below md) */}
      <nav className="md:hidden bg-white border-b border-gray-200 overflow-x-auto" aria-label="Main">
        <div className="flex px-2 py-1.5 gap-1 min-w-max">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `inline-flex items-center px-3 py-2 rounded-md text-xs font-medium whitespace-nowrap ${
                    isActive ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600'
                  }`
                }
              >
                <Icon className="w-4 h-4 mr-1.5" />
                {item.name}
              </NavLink>
            );
          })}
        </div>
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      <footer className="bg-white border-t border-gray-200 py-4 text-center text-xs text-gray-500">
        AttendX 2.0 &bull; Automated Classroom Attendance &bull; InsightFace ArcFace
      </footer>
    </div>
  );
};
