import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { api } from '../api/client';
import { Student } from '../api/types';

export const StudentsPage = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [rollNo, setRollNo] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api<Student[]>('/api/students')
      .then(setStudents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api('/api/students', { method: 'POST', body: JSON.stringify({ roll_no: rollNo, full_name: fullName }) });
      setRollNo('');
      setFullName('');
      setShowForm(false);
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const input = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Students</h1>
          <p className="text-sm text-gray-500 mt-1">A student logs in with their roll number as both username and password.</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Add Student
        </button>
      </div>

      {error && !showForm && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">{error}</div>}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-gray-600 font-semibold text-xs uppercase tracking-wider text-left">
            <tr>
              <th className="px-5 py-3">Roll No</th>
              <th className="px-5 py-3">Name</th>
              <th className="px-5 py-3">Face photos</th>
              <th className="px-5 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={4} className="px-5 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : students.length === 0 ? (
              <tr><td colSpan={4} className="px-5 py-8 text-center text-gray-400">No students yet. Click "Add Student".</td></tr>
            ) : (
              students.map((s) => (
                <tr key={s.id}>
                  <td className="px-5 py-3 font-medium text-gray-900">{s.roll_no}</td>
                  <td className="px-5 py-3 text-gray-700">{s.full_name}</td>
                  <td className={`px-5 py-3 ${s.photo_count === 0 ? 'text-red-600' : 'text-gray-600'}`}>{s.photo_count}</td>
                  <td className="px-5 py-3 text-right">
                    <Link to={`/admin/students/${s.id}`} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
                      Photos &rarr;
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <form onSubmit={add} className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Add Student</h2>
            {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">{error}</div>}
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">Roll Number</label>
              <input required value={rollNo} onChange={(e) => setRollNo(e.target.value)} className={input} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">Full Name</label>
              <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className={input} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => { setShowForm(false); setError(null); }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-xs font-semibold text-white">
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
