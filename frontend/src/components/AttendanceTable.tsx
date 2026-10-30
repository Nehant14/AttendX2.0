import { AttendanceRecord } from '../api/types';
import { StatusBadge } from './StatusBadge';

interface Props {
  records: AttendanceRecord[];
  busy: boolean;
  onToggle: (studentId: number, newStatus: 'present' | 'absent') => void;
}

export const AttendanceTable = ({ records, busy, onToggle }: Props) => (
  <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
    <table className="min-w-full divide-y divide-gray-200 text-sm">
      <thead className="bg-gray-50 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
        <tr>
          <th className="px-4 py-3">Roll No</th>
          <th className="px-4 py-3">Name</th>
          <th className="px-4 py-3">Status</th>
          <th className="px-4 py-3">Match</th>
          <th className="px-4 py-3 text-right">Change</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {records.map((r) => {
          const next = r.status === 'present' ? 'absent' : 'present';
          return (
            <tr key={r.student_id}>
              <td className="px-4 py-3 font-medium text-gray-900">{r.roll_no}</td>
              <td className="px-4 py-3 text-gray-700">{r.full_name}</td>
              <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
              <td className="px-4 py-3 font-mono text-xs text-gray-600">
                {r.similarity !== null ? `${(r.similarity * 100).toFixed(1)}%` : '—'}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  disabled={busy}
                  onClick={() => onToggle(r.student_id, next)}
                  className="px-2.5 py-1 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Mark {next === 'present' ? 'Present' : 'Absent'}
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>
);
