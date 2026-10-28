import React from 'react';
import { AttendanceRecord } from '../api/types';
import { StatusBadge } from './StatusBadge';

interface Props {
  records: AttendanceRecord[];
  onStatusChange: (studentId: number, newStatus: 'present' | 'absent') => void;
  isUpdating?: boolean;
}

export const AttendanceTable: React.FC<Props> = ({ records, onStatusChange, isUpdating }) => {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50/80 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
          <tr>
            <th className="px-5 py-3">Roll No</th>
            <th className="px-5 py-3">Name</th>
            <th className="px-5 py-3">Status</th>
            <th className="px-5 py-3">Similarity</th>
            <th className="px-5 py-3">Marked By</th>
            <th className="px-5 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {records.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-5 py-8 text-center text-gray-500">
                No attendance records for this session.
              </td>
            </tr>
          ) : (
            records.map((r) => {
              const isReview = r.status === 'needs_review';
              return (
                <tr
                  key={r.student_id}
                  className={`hover:bg-gray-50/80 transition-colors ${
                    isReview ? 'bg-amber-50/40' : ''
                  }`}
                >
                  <td className="px-5 py-3.5 font-medium text-gray-900">{r.roll_no}</td>
                  <td className="px-5 py-3.5 text-gray-700 font-medium">{r.full_name}</td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-5 py-3.5 text-gray-600 font-mono text-xs">
                    {r.similarity !== null ? (
                      <span>
                        {(r.similarity * 100).toFixed(1)}%
                        {r.margin !== null && (
                          <span
                            className={`ml-1 ${r.margin < 0 ? 'text-red-400' : 'text-gray-400'}`}
                            title="Lead over the next-best student for the same face"
                          >
                            ({r.margin >= 0 ? '+' : '-'}{Math.abs(r.margin * 100).toFixed(1)}%)
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-gray-500 capitalize text-xs">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${
                        r.marked_by === 'teacher'
                          ? 'bg-purple-50 text-purple-700 border border-purple-200'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {r.marked_by}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <select
                      value={r.status === 'needs_review' ? '' : r.status}
                      disabled={isUpdating}
                      onChange={(e) => {
                        const val = e.target.value as 'present' | 'absent';
                        if (val) {
                          onStatusChange(r.student_id, val);
                        }
                      }}
                      className="text-xs rounded-lg border border-gray-300 py-1.5 px-2 bg-white text-gray-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 font-medium cursor-pointer"
                    >
                      {r.status === 'needs_review' && <option value="">Resolve...</option>}
                      <option value="present">Mark Present</option>
                      <option value="absent">Mark Absent</option>
                    </select>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
};
