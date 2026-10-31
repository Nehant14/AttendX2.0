import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { AttendanceGrid } from '../api/types';

/** Every student x every class day. Click a date to open that class. */
export const AttendanceGridPage = () => {
  const [grid, setGrid] = useState<AttendanceGrid | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<AttendanceGrid>('/api/attendance').then(setGrid).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">{error}</div>;
  if (!grid) return <p className="text-gray-500">Loading…</p>;

  const fmt = (iso: string) => {
    const d = new Date(iso);
    return `${d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })} ${d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Attendance</h1>
        <p className="text-sm text-gray-500 mt-1">All students, all classes. Click a date to open that class.</p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-gray-600 font-semibold text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Roll No</th>
              <th className="px-4 py-3 text-left">Name</th>
              {grid.sessions.map((s) => (
                <th key={s.id} className="px-3 py-3 text-center whitespace-nowrap">
                  <Link to={`/admin/sessions/${s.id}`} className="text-indigo-600 hover:underline normal-case">
                    {fmt(s.created_at)}
                  </Link>
                </th>
              ))}
              <th className="px-4 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {grid.students.length === 0 ? (
              <tr><td colSpan={grid.sessions.length + 3} className="px-4 py-8 text-center text-gray-400">No students yet.</td></tr>
            ) : (
              grid.students.map((r) => (
                <tr key={r.student_id}>
                  <td className="px-4 py-3 font-medium text-gray-900">{r.roll_no}</td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{r.full_name}</td>
                  {r.marks.map((m, i) => (
                    <td key={i} className="px-3 py-3 text-center">
                      {m === 'present' ? (
                        <span className="font-bold text-green-600">P</span>
                      ) : m === 'absent' ? (
                        <span className="font-bold text-red-600">A</span>
                      ) : (
                        <span className="text-gray-300">–</span>
                      )}
                    </td>
                  ))}
                  <td className="px-4 py-3 text-right whitespace-nowrap text-gray-700">
                    {r.present}/{r.total} <span className="text-gray-400">({r.percentage}%)</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
