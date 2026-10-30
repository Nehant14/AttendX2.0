import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Camera } from 'lucide-react';
import { api } from '../api/client';
import { Session } from '../api/types';
import { PhotoPicker } from '../components/PhotoPicker';

export const TakeAttendancePage = () => {
  const navigate = useNavigate();
  const retake = useSearchParams()[0].get('retake'); // set when coming from "Retake attendance"
  const [photos, setPhotos] = useState<File[]>([]);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (photos.length === 0) return;
    setProcessing(true);
    setError(null);
    const form = new FormData();
    photos.forEach((p) => form.append('files', p));
    try {
      const session = await api<Session>(retake ? `/api/attendance/${retake}` : '/api/attendance', {
        method: retake ? 'PUT' : 'POST',
        body: form,
      });
      navigate(`/admin/sessions/${session.id}`);
    } catch (e: any) {
      setError(e.message);
      setProcessing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{retake ? 'Retake Attendance' : 'Take Attendance'}</h1>
        <p className="text-sm text-gray-500 mt-1">
          {retake
            ? 'Upload new photo(s) of the same class. This replaces the current result, including manual changes.'
            : 'Upload class photo(s). Add several (other sections or the back rows) for better results: a student is present if any photo matches them.'}
        </p>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-5">
        <PhotoPicker files={photos} onChange={setPhotos} />
        <button
          onClick={submit}
          disabled={photos.length === 0 || processing}
          className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center justify-center gap-2"
        >
          <Camera className="w-4 h-4" />
          {processing ? 'Detecting faces…' : retake ? 'Retake Attendance' : 'Detect Faces & Mark Attendance'}
        </button>
        {retake && (
          <Link to={`/admin/sessions/${retake}`} className="block text-center text-xs font-semibold text-gray-500 hover:text-gray-900">
            Cancel
          </Link>
        )}
      </div>
    </div>
  );
};
