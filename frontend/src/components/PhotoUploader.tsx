import { useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { api } from '../api/client';
import { PhotoUploadResponse } from '../api/types';

/** Upload face photos for one student; each accepted photo gets its embedding saved. */
export const PhotoUploader = ({ studentId, onUploaded }: { studentId: number; onUploaded: () => void }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [rejected, setRejected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const upload = async (files: FileList) => {
    setBusy(true);
    setError(null);
    setRejected([]);
    const form = new FormData();
    Array.from(files).forEach((f) => form.append('files', f));
    try {
      const res = await api<PhotoUploadResponse>(`/api/students/${studentId}/photos`, { method: 'POST', body: form });
      setRejected(res.results.filter((r) => !r.accepted).map((r) => `${r.filename}: ${r.reason}`));
      onUploaded();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 hover:border-indigo-400 rounded-xl p-6 text-center cursor-pointer"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={(e) => e.target.files && upload(e.target.files)}
        />
        <Upload className="w-7 h-7 text-indigo-500 mx-auto mb-2" />
        <span className="text-sm font-semibold text-gray-700">
          {busy ? 'Reading faces…' : 'Click to add face photos (you can select several)'}
        </span>
      </div>
      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
      {rejected.map((r) => (
        <p key={r} className="mt-3 text-xs text-red-600">{r}</p>
      ))}
    </div>
  );
};
