import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { MyAttendance } from '../api/types';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';

export const StudentDashboardPage = () => {
  const [data, setData] = useState<MyAttendance | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<MyAttendance>('/api/me/attendance').then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">{error}</div>;
  if (!data) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{data.name}</h1>
        <p className="text-sm text-gray-500 mt-1">Roll No {data.roll_no}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Classes" value={data.total} />
        <StatCard label="Present" value={data.present} color="text-green-700" />
        <StatCard label="Absent" value={data.absent} color="text-red-700" />
        <StatCard label="Attendance" value={`${data.percentage}%`} />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
            <tr>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.records.length === 0 ? (
              <tr><td colSpan={2} className="px-5 py-8 text-center text-gray-400">No attendance taken yet.</td></tr>
            ) : (
              data.records.map((r) => (
                <tr key={r.session_id}>
                  <td className="px-5 py-3 text-gray-700">{new Date(r.date).toLocaleString()}</td>
                  <td className="px-5 py-3"><StatusBadge status={r.status} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
