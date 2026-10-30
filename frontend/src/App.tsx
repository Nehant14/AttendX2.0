import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { getAuth } from './api/client';
import { Role } from './api/types';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { TakeAttendancePage } from './pages/TakeAttendancePage';
import { StudentsPage } from './pages/StudentsPage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { SessionResultPage } from './pages/SessionResultPage';
import { StudentDashboardPage } from './pages/StudentDashboardPage';

/** Only lets the given role in; anyone else goes back to the login page. */
const Guard = ({ role, children }: { role: Role; children: JSX.Element }) => {
  const auth = getAuth();
  if (!auth || auth.role !== role) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Professor / admin */}
        <Route path="/admin" element={<Guard role="admin"><TakeAttendancePage /></Guard>} />
        <Route path="/admin/students" element={<Guard role="admin"><StudentsPage /></Guard>} />
        <Route path="/admin/students/:id" element={<Guard role="admin"><StudentDetailPage /></Guard>} />
        <Route path="/admin/sessions/:id" element={<Guard role="admin"><SessionResultPage /></Guard>} />

        {/* Student */}
        <Route path="/student" element={<Guard role="student"><StudentDashboardPage /></Guard>} />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
