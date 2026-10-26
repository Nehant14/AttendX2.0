import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, ShieldCheck, CheckCircle2, AlertCircle, Image as ImageIcon } from 'lucide-react';
import { apiFetch } from '../api/client';
import { StudentDetail } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { AuthImage } from '../components/AuthImage';
import { localToday } from '../utils/date';
import { EnrollmentPhotoUploader } from '../components/EnrollmentPhotoUploader';

export const StudentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [student, setStudent] = useState<StudentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit fields
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [consentRecorded, setConsentRecorded] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchStudent = async () => {
    try {
      const data = await apiFetch<StudentDetail>(`/api/students/${id}`);
      setStudent(data);
      setFullName(data.full_name);
      setEmail(data.email || '');
      setConsentRecorded(data.consent_recorded);
    } catch (err: any) {
      setError(err.message || 'Failed to load student');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudent();
  }, [id]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(false);
    try {
      await apiFetch(`/api/students/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: fullName,
          email: email.trim() || null,
          consent_recorded: consentRecorded,
          // keep the original consent date when consent was already recorded
          consent_date: consentRecorded ? student?.consent_date || localToday() : null,
        }),
      });
      await fetchStudent();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      alert('Failed to update student: ' + err.message);
    }
  };

  const handleDeletePhoto = async (photoId: number) => {
    if (!window.confirm('Delete this enrollment photo and its face embedding?')) return;
    try {
      await apiFetch(`/api/students/${id}/photos/${photoId}`, { method: 'DELETE' });
      fetchStudent();
    } catch (err: any) {
      alert('Failed to delete photo: ' + err.message);
    }
  };

  const handleToggleActive = async () => {
    if (!student) return;
    try {
      await apiFetch(`/api/students/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !student.is_active }),
      });
      await fetchStudent();
    } catch (err: any) {
      alert('Update failed: ' + err.message);
    }
  };

  const handlePurge = async () => {
    const msg =
      'This permanently deletes the student, all enrollment photos and face data, and all of their attendance records. This cannot be undone. Continue?';
    if (!window.confirm(msg)) return;
    try {
      await apiFetch(`/api/students/${id}?purge=true`, { method: 'DELETE' });
      navigate('/students');
    } catch (err: any) {
      alert('Delete failed: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !student) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center text-red-700">
        <p className="font-semibold">{error || 'Student not found'}</p>
        <button
          onClick={() => navigate('/students')}
          className="mt-4 px-4 py-2 bg-white border border-gray-300 rounded-lg text-xs font-semibold text-gray-700"
        >
          Back to Students
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/students')}
          className="inline-flex items-center text-xs font-semibold text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Students Directory
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleActive}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50"
          >
            {student.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <button
            onClick={handlePurge}
            className="px-3 py-1.5 border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg text-xs font-semibold"
          >
            Purge Permanently
          </button>
        </div>
      </div>

      {/* Header Info */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm px-2.5 py-0.5 rounded-md bg-gray-100 text-gray-700 font-semibold">
              {student.roll_no}
            </span>
            <StatusBadge status={student.ready ? 'ready' : 'not_ready'} />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight mt-1">
            {student.full_name}
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {student.photos.length} photos enrolled &bull; {student.ready ? 'Ready for class recognition' : 'Upload at least 3 good photos (5-10 recommended)'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Photos Grid and Uploader */}
        <div className="lg:col-span-7 space-y-6">
          <EnrollmentPhotoUploader studentId={student.id} onUploaded={fetchStudent} />

          {/* Enrolled Photos Grid */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">
              Enrolled Face Photos ({student.photos.length})
            </h3>
            {student.photos.length === 0 ? (
              <div className="p-8 text-center border-2 border-dashed border-gray-200 rounded-xl">
                <ImageIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-xs text-gray-500">No enrollment photos uploaded yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {student.photos.map((p) => (
                  <div
                    key={p.id}
                    className="group relative rounded-xl overflow-hidden border border-gray-200 bg-gray-100 aspect-square shadow-xs"
                  >
                    <AuthImage
                      src={p.url}
                      alt="Enrollment photo"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleDeletePhoto(p.id)}
                        className="p-1.5 bg-red-600 text-white rounded-lg shadow-md hover:bg-red-700 transition-colors"
                        title="Delete photo"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    {p.face_px && (
                      <div className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
                        {p.face_px}px
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Student Information & Consent */}
        <div className="lg:col-span-5 space-y-6">
          <form
            onSubmit={handleUpdate}
            className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4"
          >
            <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-2">
              Edit Details
            </h3>

            {saveSuccess && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700 font-medium">
                Changes saved successfully.
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                Full Name
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-600" />
                <span className="text-xs font-bold text-gray-800 uppercase tracking-wider">
                  Biometrics Consent
                </span>
              </div>
              <p className="text-[11px] text-gray-500">
                In compliance with DPDP data privacy standards, written consent must be verified for facial recognition attendance.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="consentDetail"
                  checked={consentRecorded}
                  onChange={(e) => setConsentRecorded(e.target.checked)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="consentDetail" className="text-xs text-gray-700 font-medium cursor-pointer">
                  Consent recorded{student.consent_date ? ` (${student.consent_date})` : ''}
                </label>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 rounded-xl text-xs font-semibold text-white shadow-sm transition-colors cursor-pointer"
            >
              Update Student Info
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
