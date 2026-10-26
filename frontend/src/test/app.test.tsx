import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { StudentDetailPage } from '../pages/StudentDetailPage';
import { HistoryPage } from '../pages/HistoryPage';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AuthImage } from '../components/AuthImage';
import { TOKEN_KEY } from '../api/client';
import { localToday } from '../utils/date';
import { headerOf, json, mockFetch } from './helpers';

const student = {
  id: 7, roll_no: 'R07', full_name: 'Ada Lovelace', email: null, is_active: true,
  consent_recorded: true, consent_date: '2026-10-01', embedding_count: 3, ready: true,
};

describe('LoginPage', () => {
  it('shows the server message on a wrong password and stays on the page', async () => {
    mockFetch({
      'GET /api/auth/me': () => json({ detail: 'Not authenticated', code: 'UNAUTHORIZED' }, 401),
      'POST /api/auth/login': () => json({ detail: 'Incorrect email or password.', code: 'UNAUTHORIZED' }, 401),
    });
    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    await userEvent.type(screen.getByPlaceholderText('teacher@example.com'), 'a@b.co');
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'bad');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText('Incorrect email or password.')).toBeTruthy();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it('stores the token on success', async () => {
    mockFetch({
      'GET /api/auth/me': () => json({ detail: 'x', code: 'UNAUTHORIZED' }, 401),
      'POST /api/auth/login': () =>
        json({ access_token: 'tok123', token_type: 'bearer', user: { id: 1, email: 'a@b.co', role: 'admin' } }),
    });
    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    await userEvent.type(screen.getByPlaceholderText('teacher@example.com'), 'a@b.co');
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(localStorage.getItem(TOKEN_KEY)).toBe('tok123'));
  });
});

describe('ProtectedRoute', () => {
  const tree = (
    <MemoryRouter initialEntries={['/secret']}>
      <Routes>
        <Route path="/login" element={<div>LOGIN PAGE</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/secret" element={<div>SECRET</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );

  it('lets everyone in when auth is disabled on the server', async () => {
    mockFetch({ 'GET /api/auth/me': () => json({ id: 0, email: 'demo@example.com', role: 'admin' }) });
    render(tree);
    expect(await screen.findByText('SECRET')).toBeTruthy();
  });

  it('redirects to /login when the server answers 401', async () => {
    mockFetch({ 'GET /api/auth/me': () => json({ detail: 'Not authenticated', code: 'UNAUTHORIZED' }, 401) });
    render(tree);
    expect(await screen.findByText('LOGIN PAGE')).toBeTruthy();
  });
});

describe('AuthImage', () => {
  it('fetches protected images with the Authorization header', async () => {
    localStorage.setItem(TOKEN_KEY, 'tok123');
    const { calls } = mockFetch({
      'GET /files/sessions/1/annotated.jpg': () =>
        new Response(new Blob(['x'], { type: 'image/jpeg' }), { status: 200 }),
    });
    render(<AuthImage src="/files/sessions/1/annotated.jpg" alt="annotated" />);
    const img = await screen.findByAltText('annotated');
    expect(img.getAttribute('src')).toBe('blob:mock-url');
    expect(headerOf(calls[0].init, 'Authorization')).toBe('Bearer tok123');
  });
});

describe('StudentDetailPage', () => {
  it('survives saving (PATCH returns no photos) and keeps rendering photos', async () => {
    localStorage.setItem(TOKEN_KEY, 'tok');
    const detail = { ...student, photos: [{ id: 1, url: '/files/enrollment/7/a.jpg', det_score: 0.9, face_px: 120 }] };
    const { calls } = mockFetch({
      'GET /api/students/7': () => json(detail),
      'PATCH /api/students/7': () => json(student),            // StudentOut: NO photos field
      'GET /files/enrollment/7/a.jpg': () => new Response(new Blob(['x'], { type: 'image/jpeg' })),
    });
    render(
      <MemoryRouter initialEntries={['/students/7']}>
        <Routes><Route path="/students/:id" element={<StudentDetailPage />} /></Routes>
      </MemoryRouter>
    );
    await screen.findByText('Ada Lovelace');
    await userEvent.click(screen.getByRole('button', { name: /update student info/i }));
    expect(await screen.findByText(/changes saved successfully/i)).toBeTruthy();
    expect(screen.getByText(/Enrolled Face Photos \(1\)/)).toBeTruthy();   // would have crashed before
    const patch = calls.find((c) => c.method === 'PATCH')!;
    // original consent date is preserved rather than overwritten with today
    expect(JSON.parse(patch.init!.body as string).consent_date).toBe('2026-10-01');
  });

  it('Deactivate sends is_active=false via PATCH (not a DELETE)', async () => {
    const { calls } = mockFetch({
      'GET /api/students/7': () => json({ ...student, photos: [] }),
      'PATCH /api/students/7': () => json({ ...student, is_active: false }),
    });
    render(
      <MemoryRouter initialEntries={['/students/7']}>
        <Routes><Route path="/students/:id" element={<StudentDetailPage />} /></Routes>
      </MemoryRouter>
    );
    await screen.findByText('Ada Lovelace');
    await userEvent.click(screen.getByRole('button', { name: 'Deactivate' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true));
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false);
    expect(JSON.parse(calls.find((c) => c.method === 'PATCH')!.init!.body as string)).toEqual({ is_active: false });
  });
});

describe('HistoryPage export', () => {
  it('downloads the CSV through fetch with the JWT and the active filters', async () => {
    localStorage.setItem(TOKEN_KEY, 'tok123');
    const { calls } = mockFetch({
      'GET /api/courses': () => json([{ id: 3, code: 'CS101', name: 'Intro', student_count: 1 }]),
      'GET /api/students': () => json([student]),
      'GET /api/sessions': () => json([]),
      'GET /api/attendance/export.csv': () =>
        new Response('\ufeffa,b\r\n', {
          headers: { 'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="x.csv"' },
        }),
    });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    render(<MemoryRouter><HistoryPage /></MemoryRouter>);
    await screen.findByText(/Attendance History/);
    await userEvent.selectOptions(screen.getAllByRole('combobox')[0], '3');
    await userEvent.selectOptions(screen.getAllByRole('combobox')[1], '7');
    await userEvent.click(screen.getByRole('button', { name: /export csv/i }));
    await waitFor(() => expect(calls.some((c) => c.url.includes('/export.csv'))).toBe(true));
    const exp = calls.find((c) => c.url.includes('/export.csv'))!;
    expect(headerOf(exp.init, 'Authorization')).toBe('Bearer tok123');
    expect(exp.url).toContain('course_id=3');
    expect(exp.url).toContain('student_id=7');
  });
});

describe('localToday', () => {
  it('uses the local calendar date, not UTC', () => {
    vi.useFakeTimers();
    // 23:30 local on the 5th is already the 6th in UTC for zones ahead of UTC (e.g. IST would be the reverse);
    // either way the result must equal the LOCAL y/m/d.
    vi.setSystemTime(new Date(2026, 9, 5, 23, 30, 0));
    expect(localToday()).toBe('2026-10-05');
    vi.setSystemTime(new Date(2026, 9, 6, 0, 10, 0));
    expect(localToday()).toBe('2026-10-06');
    vi.useRealTimers();
  });
});
