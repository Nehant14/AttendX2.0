import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, Calendar, Filter, Users, Clock, ArrowRight } from 'lucide-react';
import { apiFetch, downloadFile } from '../api/client';
import { AttendanceSummary, Course, SessionSummary, Student } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';

export const HistoryPage: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');

  const [activeTab, setActiveTab] = useState<'sessions' | 'summary'>('sessions');
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [summary, setSummary] = useState<AttendanceSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiFetch<Course[]>('/api/courses')
      .then((data) => {
        setCourses(data);
      })
      .catch((e) => setLoadError(e.message));
    apiFetch<Student[]>('/api/students')
      .then(setStudents)
      .catch((e) => setLoadError(e.message));
  }, []);

  const buildParams = () => {
    const params = new URLSearchParams();
    if (selectedCourseId) params.append('course_id', selectedCourseId);
    if (selectedStudentId) params.append('student_id', selectedStudentId);
    if (fromDate) params.append('from', fromDate);
    if (toDate) params.append('to', toDate);
    return params;
  };

  const handleExport = async () => {
    try {
      await downloadFile(`/api/attendance/export.csv?${buildParams().toString()}`, 'attendance_history.csv');
    } catch (err: any) {
      alert('Export failed: ' + err.message);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setLoadError(null);
    const params = buildParams();

    try {
      if (activeTab === 'sessions') {
        const data = await apiFetch<SessionSummary[]>(`/api/sessions?${params.toString()}`);
        setSessions(data);
      } else {
        const data = await apiFetch<AttendanceSummary[]>(`/api/attendance/summary?${params.toString()}`);
        setSummary(data);
      }
    } catch (err: any) {
      setLoadError(err.message || 'Failed to load history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedCourseId, selectedStudentId, fromDate, toDate, activeTab]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Attendance History</h1>
          <p className="text-sm text-gray-500 mt-1">
            Browse past class attendance sessions and generate cumulative student reports.
          </p>
        </div>
        <button
          onClick={handleExport}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-xl shadow-sm text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          <Download className="w-4 h-4 mr-1.5 text-gray-500" />
          Export CSV
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            Filter by Course
          </label>
          <select
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} - {c.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            Filter by Student
          </label>
          <select
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Students</option>
            {students.map((st) => (
              <option key={st.id} value={st.id}>
                {st.roll_no} - {st.full_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            From Date
          </label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            To Date
          </label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {loadError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">{loadError}</div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 space-x-6 text-sm">
        <button
          onClick={() => setActiveTab('sessions')}
          className={`pb-3 font-semibold text-xs uppercase tracking-wider transition-colors cursor-pointer ${
            activeTab === 'sessions'
              ? 'border-b-2 border-indigo-600 text-indigo-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Past Sessions
        </button>
        <button
          onClick={() => setActiveTab('summary')}
          className={`pb-3 font-semibold text-xs uppercase tracking-wider transition-colors cursor-pointer ${
            activeTab === 'summary'
              ? 'border-b-2 border-indigo-600 text-indigo-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Student Cumulative Summary
        </button>
      </div>

      {/* Content based on tab */}
      {loading ? (
        <div className="p-12 text-center text-gray-400 text-sm">Loading history data...</div>
      ) : activeTab === 'sessions' ? (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50/80 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
              <tr>
                <th className="px-5 py-3.5">Date</th>
                <th className="px-5 py-3.5">Period</th>
                <th className="px-5 py-3.5">Course</th>
                <th className="px-5 py-3.5">Present</th>
                <th className="px-5 py-3.5">Review</th>
                <th className="px-5 py-3.5">Absent</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5 text-right">View</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-gray-400">
                    No sessions match the selected filters.
                  </td>
                </tr>
              ) : (
                sessions.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900">{s.session_date}</td>
                    <td className="px-5 py-3.5 text-gray-600">Period {s.period}</td>
                    <td className="px-5 py-3.5 font-semibold text-gray-800">{s.course_code}</td>
                    <td className="px-5 py-3.5 text-green-700 font-medium">{s.present}</td>
                    <td className="px-5 py-3.5 text-amber-600 font-medium">{s.needs_review}</td>
                    <td className="px-5 py-3.5 text-red-600 font-medium">{s.absent}</td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/sessions/${s.id}`}
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 inline-flex items-center"
                      >
                        Inspect
                        <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50/80 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
              <tr>
                <th className="px-5 py-3.5">Roll No</th>
                <th className="px-5 py-3.5">Full Name</th>
                <th className="px-5 py-3.5">Total Sessions</th>
                <th className="px-5 py-3.5">Present</th>
                <th className="px-5 py-3.5">Absent</th>
                <th className="px-5 py-3.5">Attendance Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-400">
                    No attendance records for the selected filters.
                  </td>
                </tr>
              ) : (
                summary.map((row) => (
                  <tr key={row.roll_no} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900">{row.roll_no}</td>
                    <td className="px-5 py-3.5 text-gray-800 font-medium">{row.full_name}</td>
                    <td className="px-5 py-3.5 text-gray-600">{row.sessions}</td>
                    <td className="px-5 py-3.5 text-green-700 font-medium">{row.present}</td>
                    <td className="px-5 py-3.5 text-red-600 font-medium">{row.absent}</td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-semibold text-xs ${
                            row.percent >= 75
                              ? 'text-green-700'
                              : row.percent >= 60
                              ? 'text-amber-600'
                              : 'text-red-600'
                          }`}
                        >
                          {row.percent}%
                        </span>
                        <div className="w-16 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              row.percent >= 75
                                ? 'bg-green-600'
                                : row.percent >= 60
                                ? 'bg-amber-500'
                                : 'bg-red-500'
                            }`}
                            style={{ width: `${Math.min(row.percent, 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
