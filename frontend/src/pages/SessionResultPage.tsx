import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { Session } from '../api/types';
import { AttendanceTable } from '../components/AttendanceTable';
import { ImageViewer } from '../components/ImageViewer';
import { StatCard } from '../components/StatCard';

export const SessionResultPage = () => {
  const { id } = useParams();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Session>(`/api/attendance/${id}`).then(setSession).catch((e) => setError(e.message));
  }, [id]);

  const setStatus = async (studentId: number, status: 'present' | 'absent') => {
    setBusy(true);
    try {
      setSession(await api<Session>(`/api/attendance/${id}/records/${studentId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }));
    } catch (e: any) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (error) return <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">{error}</div>;
  if (!session) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Attendance Result</h1>
          <p className="text-sm text-gray-500 mt-1">{new Date(session.created_at).toLocaleString()}</p>
        </div>
        <Link
          to={`/admin?retake=${session.id}`}
          className="inline-flex items-center px-3.5 py-2 border border-gray-300 rounded-xl text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50"
        >
          <RefreshCw className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
          Retake attendance
        </Link>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total" value={session.total} />
        <StatCard label="Present" value={session.present} color="text-green-700" />
        <StatCard label="Absent" value={session.absent} color="text-red-700" />
        <StatCard
          label="Avg match"
          value={session.avg_match !== null ? `${(session.avg_match * 100).toFixed(1)}%` : '—'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7">
          <ImageViewer key={session.image_urls.join()} srcs={session.image_urls} />
        </div>
        <div className="lg:col-span-5">
          <AttendanceTable records={session.records} busy={busy} onToggle={setStatus} />
        </div>
      </div>
    </div>
  );
};
