import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { TakeAttendancePage } from './pages/TakeAttendancePage';
import { StudentsPage } from './pages/StudentsPage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { CoursesPage } from './pages/CoursesPage';
import { SessionResultPage } from './pages/SessionResultPage';
import { HistoryPage } from './pages/HistoryPage';

const queryClient = new QueryClient();

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute />}>
            <Route
              path="/"
              element={
                <Layout>
                  <TakeAttendancePage />
                </Layout>
              }
            />
            <Route
              path="/students"
              element={
                <Layout>
                  <StudentsPage />
                </Layout>
              }
            />
            <Route
              path="/students/:id"
              element={
                <Layout>
                  <StudentDetailPage />
                </Layout>
              }
            />
            <Route
              path="/courses"
              element={
                <Layout>
                  <CoursesPage />
                </Layout>
              }
            />
            <Route
              path="/sessions/:id"
              element={
                <Layout>
                  <SessionResultPage />
                </Layout>
              }
            />
            <Route
              path="/history"
              element={
                <Layout>
                  <HistoryPage />
                </Layout>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
