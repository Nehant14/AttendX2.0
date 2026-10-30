import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { StudentDetail } from '../api/types';
import { PhotoUploader } from '../components/PhotoUploader';

export const StudentDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [student, setStudent] = useState<StudentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api<StudentDetail>(`/api/students/${id}`).then(setStudent).catch((e) => setError(e.message));

  useEffect(() => { load(); }, [id]);

  const deletePhoto = async (photoId: number) => {
    await api(`/api/students/${id}/photos/${photoId}`, { method: 'DELETE' });
    load();
  };

  const deleteStudent = async () => {
    if (!window.confirm('Delete this student, their photos and their attendance records?')) return;
    await api(`/api/students/${id}`, { method: 'DELETE' });
    navigate('/admin/students');
  };

  if (error) return <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">{error}</div>;
  if (!student) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/admin/students" className="inline-flex items-center text-xs font-semibold text-gray-500 hover:text-gray-900">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to students
        </Link>
        <button
          onClick={deleteStudent}
          className="px-3 py-1.5 border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg text-xs font-semibold"
        >
          Delete student
        </button>
      </div>

      <div>
        <span className="font-mono text-sm px-2.5 py-0.5 rounded-md bg-gray-100 text-gray-700 font-semibold">{student.roll_no}</span>
        <h1 className="text-2xl font-bold text-gray-900 mt-1">{student.full_name}</h1>
      </div>

      <PhotoUploader studentId={student.id} onUploaded={load} />

      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">Face photos ({student.photos.length})</h3>
        {student.photos.length === 0 ? (
          <p className="text-xs text-gray-500">No photos yet. Without photos this student will always be absent.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {student.photos.map((p) => (
              <div key={p.id} className="group relative rounded-xl overflow-hidden border border-gray-200 aspect-square bg-gray-100">
                <img src={p.url} alt="Face" className="w-full h-full object-cover" />
                <button
                  onClick={() => deletePhoto(p.id)}
                  className="absolute top-1.5 right-1.5 p-1.5 bg-red-600 text-white rounded-lg opacity-0 group-hover:opacity-100 focus:opacity-100"
                  title="Delete photo"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
