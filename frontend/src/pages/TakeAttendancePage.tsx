import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera } from 'lucide-react';
import { api } from '../api/client';
import { Session } from '../api/types';
import { ImageDropzone } from '../components/ImageDropzone';

export const TakeAttendancePage = () => {
  const navigate = useNavigate();
  const [photo, setPhoto] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!photo) return;
    setProcessing(true);
    setError(null);
    const form = new FormData();
    form.append('file', photo);
    try {
      const session = await api<Session>('/api/attendance', { method: 'POST', body: form });
      navigate(`/admin/sessions/${session.id}`);
    } catch (e: any) {
      setError(e.message);
      setProcessing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Take Attendance</h1>
        <p className="text-sm text-gray-500 mt-1">Upload a class photo. Every student you have added is checked against it.</p>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-5">
        <ImageDropzone file={photo} onChange={setPhoto} />
        <button
          onClick={submit}
          disabled={!photo || processing}
          className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center justify-center gap-2"
        >
          <Camera className="w-4 h-4" />
          {processing ? 'Detecting faces…' : 'Detect Faces & Mark Attendance'}
        </button>
      </div>
    </div>
  );
};
