import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download, RefreshCw, Trash2, AlertTriangle, Users, CheckCircle, HelpCircle, XCircle } from 'lucide-react';
import { apiFetch, downloadFile } from '../api/client';
import { SessionData } from '../api/types';
import { AnnotatedImageViewer } from '../components/AnnotatedImageViewer';
import { AttendanceTable } from '../components/AttendanceTable';

export const SessionResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchSession = async () => {
    try {
      const data = await apiFetch<SessionData>(`/api/sessions/${id}`);
      setSession(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load session details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSession();
  }, [id]);

  const handleStatusChange = async (studentId: number, newStatus: 'present' | 'absent') => {
    if (!session) return;
    setIsUpdating(true);

    // Optimistic update
    const previousSession = { ...session };
    const updatedRecords = session.records.map((r) =>
      r.student_id === studentId ? { ...r, status: newStatus, marked_by: 'teacher' as const } : r
    );
    setSession({ ...session, records: updatedRecords });

    try {
      const updated = await apiFetch<SessionData>(`/api/sessions/${id}/records/${studentId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      setSession(updated);
    } catch (err: any) {
      alert('Failed to update attendance status: ' + err.message);
      setSession(previousSession);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDeleteSession = async () => {
    if (!window.confirm('Are you sure you want to delete this attendance session and all records?')) {
      return;
    }
    try {
      await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' });
      navigate('/history');
    } catch (err: any) {
      alert('Failed to delete session: ' + err.message);
    }
  };

  const handleExport = async () => {
    try {
      await downloadFile(`/api/sessions/${id}/export.csv`, `attendance_session_${id}.csv`);
    } catch (err: any) {
      alert('Export failed: ' + err.message);
    }
  };

  const handleReprocess = () => {
    if (!session) return;
    navigate(
      `/?course_id=${session.course.id}&date=${session.session_date}&period=${session.period}&replace=true`
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center text-red-700">
        <p className="font-semibold">{error || 'Session not found'}</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 bg-white border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50 shadow-sm"
        >
          Back to Take Attendance
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header and Actions */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">
              {session.course.code}
            </span>
            <span className="text-sm text-gray-500 font-medium">
              {session.session_date} &bull; Period {session.period}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight mt-1">
            {session.course.name}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleExport}
            className="inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-xl shadow-sm text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
            Export CSV
          </button>
          <button
            onClick={handleReprocess}
            className="inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-xl shadow-sm text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
            Re-process with a new photo
          </button>
          <button
            onClick={handleDeleteSession}
            className="inline-flex items-center px-3.5 py-2 border border-red-200 rounded-xl shadow-sm text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
            Delete
          </button>
        </div>
      </div>

      {/* Banner if present */}
      {session.banner && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3 text-sm text-amber-800">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-600" />
          <span className="font-medium">{session.banner}</span>
        </div>
      )}

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Enrolled</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{session.counts.enrolled}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-green-600 uppercase tracking-wider">Present</div>
          <div className="text-2xl font-bold text-green-700 mt-1">{session.counts.present}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Review</div>
          <div className="text-2xl font-bold text-amber-700 mt-1">{session.counts.needs_review}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-red-600 uppercase tracking-wider">Absent</div>
          <div className="text-2xl font-bold text-red-700 mt-1">{session.counts.absent}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Detected</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{session.counts.faces_detected}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Unknown</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{session.counts.unknown_faces}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Too Small</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{session.counts.unrecognizable_faces}</div>
        </div>
      </div>

      {/* Main split: Image Viewer and Attendance Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7">
          <AnnotatedImageViewer
            annotatedUrl={session.annotated_url}
            originalUrl={session.original_url}
          />
        </div>
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
            <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              Student Attendance List
            </span>
            <span className="text-xs text-gray-500">
              Processed in {session.processing_ms ? `${session.processing_ms}ms` : '—'}
            </span>
          </div>
          <AttendanceTable
            records={session.records}
            onStatusChange={handleStatusChange}
            isUpdating={isUpdating}
          />
        </div>
      </div>
    </div>
  );
};
