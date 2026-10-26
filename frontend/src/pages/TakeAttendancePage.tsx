import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Camera, Calendar, Clock, BookOpen, AlertCircle, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import { Course, SessionData } from '../api/types';
import { ImageDropzone } from '../components/ImageDropzone';
import { localToday } from '../utils/date';

export const TakeAttendancePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>('');
  const [sessionDate, setSessionDate] = useState<string>(localToday());
  const [period, setPeriod] = useState<number>(1);
  const [replace, setReplace] = useState<boolean>(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [processing, setProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Populate parameters from URL if present (e.g., from "Re-process with a new photo")
    const courseParam = searchParams.get('course_id');
    const dateParam = searchParams.get('date');
    const periodParam = searchParams.get('period');
    const replaceParam = searchParams.get('replace');

    if (courseParam) setSelectedCourseId(courseParam);
    if (dateParam) setSessionDate(dateParam);
    if (periodParam) setPeriod(parseInt(periodParam, 10));
    if (replaceParam === 'true') setReplace(true);

    apiFetch<Course[]>('/api/courses')
      .then((data) => {
        setCourses(data);
        if (!selectedCourseId && data.length > 0 && !courseParam) {
          setSelectedCourseId(data[0].id.toString());
        }
      })
      .catch((err) => {
        setError('Failed to load courses: ' + err.message);
      });
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourseId) {
      setError('Please select a course.');
      return;
    }
    if (!photo) {
      setError('Please select or drop a classroom photo.');
      return;
    }
    if (!sessionDate) {
      setError('Please choose a session date.');
      return;
    }

    setProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append('course_id', selectedCourseId);
    formData.append('session_date', sessionDate);
    formData.append('period', period.toString());
    formData.append('replace', replace.toString());
    formData.append('file', photo);

    try {
      const session = await apiFetch<SessionData>('/api/sessions', {
        method: 'POST',
        body: formData,
      });
      navigate(`/sessions/${session.id}`);
    } catch (err: any) {
      if (err.code === 'SESSION_EXISTS') setReplace(true);
      setError(
        err.code === 'SESSION_EXISTS'
          ? `${err.message} The overwrite option is now ticked; submit again to replace it.`
          : err.message || 'Failed to process attendance photo.'
      );
      setProcessing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Take Attendance</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload a classroom photo to detect faces and automatically recognize enrolled students.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-sm text-red-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" />
          <div>{error}</div>
        </div>
      )}

      {processing ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-sm">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-50 text-indigo-600 mb-4 animate-pulse">
            <Camera className="w-8 h-8 animate-bounce" />
          </div>
          <h2 className="text-lg font-bold text-gray-900 mb-2">Processing Attendance Photo</h2>
          <p className="text-sm text-gray-500 max-w-sm mx-auto">
            Processing, this takes a few seconds. Please keep this page open.
          </p>
          <div className="mt-6 flex justify-center">
            <div className="w-48 bg-gray-100 rounded-full h-2 overflow-hidden">
              <div className="bg-indigo-600 h-full rounded-full animate-[indeterminate_1.5s_infinite_linear]"></div>
            </div>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8 shadow-sm space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Course
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <BookOpen className="w-4 h-4" />
                </div>
                <select
                  value={selectedCourseId}
                  onChange={(e) => setSelectedCourseId(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 font-medium"
                >
                  {courses.length === 0 ? (
                    <option value="">No courses created</option>
                  ) : (
                    courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code} - {c.name} ({c.student_count} students)
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Session Date
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Calendar className="w-4 h-4" />
                </div>
                <input
                  type="date"
                  value={sessionDate}
                  onChange={(e) => setSessionDate(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 font-medium"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                Period / Slot
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Clock className="w-4 h-4" />
                </div>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={period}
                  onChange={(e) => setPeriod(parseInt(e.target.value, 10) || 1)}
                  className="w-full pl-9 pr-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 font-medium"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
              Classroom Photo
            </label>
            <ImageDropzone onFileSelect={setPhoto} selectedFile={photo} />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="replace"
              checked={replace}
              onChange={(e) => setReplace(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="replace" className="text-xs text-gray-600 cursor-pointer select-none">
              Overwrite existing session if attendance was already recorded for this course, date, and period.
            </label>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={!photo || !selectedCourseId}
              className="w-full py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-all cursor-pointer flex items-center justify-center gap-2"
            >
              <Camera className="w-4 h-4" />
              Recognize Faces & Record Attendance
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
