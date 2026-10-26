import React, { useEffect, useState } from 'react';
import { Plus, BookOpen, Users, Check, Search } from 'lucide-react';
import { apiFetch } from '../api/client';
import { Course, CourseDetail, Student } from '../api/types';

export const CoursesPage: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<CourseDetail | null>(null);
  const [selectedStudentIds, setSelectedStudentIds] = useState<Set<number>>(new Set());

  const [loading, setLoading] = useState(true);
  const [searchStudent, setSearchStudent] = useState('');

  // Add Course Modal
  const [showAddCourse, setShowAddCourse] = useState(false);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [coursesData, studentsData] = await Promise.all([
        apiFetch<Course[]>('/api/courses'),
        apiFetch<Student[]>('/api/students'),
      ]);
      setCourses(coursesData);
      setStudents(studentsData);

      if (coursesData.length > 0 && !selectedCourse) {
        loadCourseDetail(coursesData[0].id);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadCourseDetail = async (courseId: number) => {
    try {
      const detail = await apiFetch<CourseDetail>(`/api/courses/${courseId}`);
      setSelectedCourse(detail);
      setSelectedStudentIds(new Set(detail.students.map((s) => s.id)));
    } catch (err: any) {
      alert('Failed to load course details: ' + err.message);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    try {
      const newCourse = await apiFetch<Course>('/api/courses', {
        method: 'POST',
        body: JSON.stringify({ code, name }),
      });
      setShowAddCourse(false);
      setCode('');
      setName('');
      fetchData();
      loadCourseDetail(newCourse.id);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create course');
    }
  };

  const toggleStudent = (id: number) => {
    const next = new Set(selectedStudentIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedStudentIds(next);
  };

  const handleSaveRoster = async () => {
    if (!selectedCourse) return;
    try {
      const updated = await apiFetch<CourseDetail>(`/api/courses/${selectedCourse.id}/students`, {
        method: 'PUT',
        body: JSON.stringify({ student_ids: Array.from(selectedStudentIds) }),
      });
      setSelectedCourse(updated);
      fetchData();
      alert('Course roster updated successfully.');
    } catch (err: any) {
      alert('Failed to update roster: ' + err.message);
    }
  };

  const filteredStudents = students.filter(
    (s) =>
      s.full_name.toLowerCase().includes(searchStudent.toLowerCase()) ||
      s.roll_no.toLowerCase().includes(searchStudent.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Courses & Rosters</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage course offerings and assign enrolled student rosters.
          </p>
        </div>
        <button
          onClick={() => setShowAddCourse(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Create Course
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Courses List */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-2">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider px-2">
            All Courses ({courses.length})
          </span>
          {courses.length === 0 ? (
            <p className="text-xs text-gray-400 p-4 text-center">No courses created yet.</p>
          ) : (
            courses.map((c) => (
              <div
                key={c.id}
                onClick={() => loadCourseDetail(c.id)}
                className={`p-3.5 rounded-xl cursor-pointer border transition-all ${
                  selectedCourse?.id === c.id
                    ? 'bg-indigo-50/70 border-indigo-200 shadow-xs'
                    : 'bg-white border-transparent hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-gray-900">{c.code}</span>
                  <span className="text-xs text-gray-500 flex items-center">
                    <Users className="w-3.5 h-3.5 mr-1 text-gray-400" />
                    {c.student_count} students
                  </span>
                </div>
                <div className="text-xs text-gray-600 mt-0.5 truncate">{c.name}</div>
              </div>
            ))
          )}
        </div>

        {/* Right: Roster Management for Selected Course */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
          {selectedCourse ? (
            <>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-gray-100 pb-4 gap-2">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">
                    {selectedCourse.code}: {selectedCourse.name}
                  </h2>
                  <p className="text-xs text-gray-500">
                    {selectedStudentIds.size} of {students.length} students enrolled
                  </p>
                </div>
                <button
                  onClick={handleSaveRoster}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                >
                  Save Roster Changes
                </button>
              </div>

              {/* Student Filter Search */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Search className="w-3.5 h-3.5" />
                </div>
                <input
                  type="text"
                  value={searchStudent}
                  onChange={(e) => setSearchStudent(e.target.value)}
                  placeholder="Filter students to assign..."
                  className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Students Checkbox List */}
              <div className="border border-gray-200 rounded-xl max-h-[450px] overflow-y-auto divide-y divide-gray-100">
                {filteredStudents.map((s) => {
                  const isChecked = selectedStudentIds.has(s.id);
                  return (
                    <div
                      key={s.id}
                      onClick={() => toggleStudent(s.id)}
                      className={`p-3 flex items-center justify-between text-xs cursor-pointer hover:bg-gray-50 transition-colors ${
                        isChecked ? 'bg-indigo-50/30' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-4 h-4 rounded flex items-center justify-center border ${
                            isChecked
                              ? 'bg-indigo-600 border-indigo-600 text-white'
                              : 'border-gray-300 bg-white'
                          }`}
                        >
                          {isChecked && <Check className="w-3 h-3" />}
                        </div>
                        <div>
                          <span className="font-semibold text-gray-900">{s.roll_no}</span>
                          <span className="text-gray-600 ml-2">{s.full_name}</span>
                        </div>
                      </div>
                      <span className="text-[11px] text-gray-400">
                        {s.embedding_count} photos enrolled
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-gray-400 text-sm">
              Select or create a course to manage its roster.
            </div>
          )}
        </div>
      </div>

      {/* Add Course Modal */}
      {showAddCourse && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Create New Course</h2>

            {createError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateCourse} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Course Code *
                </label>
                <input
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.toUpperCase())}
                  placeholder="e.g. CS101"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Course Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Intro to Computer Science"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddCourse(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-xs font-semibold text-white shadow-sm"
                >
                  Create Course
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
