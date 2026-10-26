import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, CheckCircle2, AlertCircle, UserCheck, UserX } from 'lucide-react';
import { apiFetch } from '../api/client';
import { Student } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { localToday } from '../utils/date';

export const StudentsPage: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // New Student Form
  const [rollNo, setRollNo] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [consentRecorded, setConsentRecorded] = useState(true);
  const [addError, setAddError] = useState<string | null>(null);

  const fetchStudents = async () => {
    try {
      const data = await apiFetch<Student[]>(`/api/students?query=${encodeURIComponent(query)}`);
      setStudents(data);
      setLoadError(null);
    } catch (err: any) {
      setLoadError(err.message || 'Failed to load students.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchStudents();
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError(null);
    try {
      await apiFetch<Student>('/api/students', {
        method: 'POST',
        body: JSON.stringify({
          roll_no: rollNo,
          full_name: fullName,
          email: email || null,
          consent_recorded: consentRecorded,
          consent_date: consentRecorded ? localToday() : null,
        }),
      });
      setShowAddModal(false);
      setRollNo('');
      setFullName('');
      setEmail('');
      fetchStudents();
    } catch (err: any) {
      setAddError(err.message || 'Failed to add student.');
    }
  };

  const toggleStudentActive = async (student: Student, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiFetch(`/api/students/${student.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !student.is_active }),
      });
      fetchStudents();
    } catch (err: any) {
      alert('Failed to update student: ' + err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Students Directory</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage student records and biometrics enrollment photos.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-xl shadow-sm text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Add Student
        </button>
      </div>

      {/* Search Input */}
      <div className="relative max-w-md">
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
          <Search className="w-4 h-4" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by student name or roll number..."
          className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 shadow-sm"
        />
      </div>

      {/* Students Table */}
      {loadError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">{loadError}</div>
      )}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50/80 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
            <tr>
              <th className="px-5 py-3.5">Roll No</th>
              <th className="px-5 py-3.5">Full Name</th>
              <th className="px-5 py-3.5">Photos Enrolled</th>
              <th className="px-5 py-3.5">Recognition Status</th>
              <th className="px-5 py-3.5">Consent</th>
              <th className="px-5 py-3.5">Active</th>
              <th className="px-5 py-3.5 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-gray-400">
                  Loading students...
                </td>
              </tr>
            ) : students.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-gray-400">
                  No students found. Click "Add Student" to create one.
                </td>
              </tr>
            ) : (
              students.map((s) => (
                <tr
                  key={s.id}
                  className={`hover:bg-gray-50/80 transition-colors ${
                    !s.is_active ? 'opacity-60 bg-gray-50/40' : ''
                  }`}
                >
                  <td className="px-5 py-3.5 font-medium text-gray-900">{s.roll_no}</td>
                  <td className="px-5 py-3.5 text-gray-800 font-medium">{s.full_name}</td>
                  <td className="px-5 py-3.5 text-gray-600 font-medium">
                    {s.embedding_count} photos
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={s.ready ? 'ready' : 'not_ready'} />
                  </td>
                  <td className="px-5 py-3.5">
                    {s.consent_recorded ? (
                      <span className="inline-flex items-center text-xs text-green-700 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                        Recorded
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-xs text-amber-600 font-medium">
                        <AlertCircle className="w-3.5 h-3.5 mr-1" />
                        Pending
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <button
                      onClick={(e) => toggleStudentActive(s, e)}
                      className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded cursor-pointer ${
                        s.is_active
                          ? 'text-green-700 bg-green-50 hover:bg-green-100'
                          : 'text-gray-500 bg-gray-100 hover:bg-gray-200'
                      }`}
                    >
                      {s.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link
                      to={`/students/${s.id}`}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                    >
                      Manage &rarr;
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add Student Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add New Student</h2>

            {addError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
                {addError}
              </div>
            )}

            <form onSubmit={handleAddStudent} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Roll Number *
                </label>
                <input
                  type="text"
                  required
                  value={rollNo}
                  onChange={(e) => setRollNo(e.target.value)}
                  placeholder="e.g. CS2026-042"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jane Doe"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jane@example.com"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="consent"
                  checked={consentRecorded}
                  onChange={(e) => setConsentRecorded(e.target.checked)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="consent" className="text-xs text-gray-600 cursor-pointer">
                  Student biometric consent recorded (DPDP Act compliance)
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-xs font-semibold text-white shadow-sm"
                >
                  Save Student
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
