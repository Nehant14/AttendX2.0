export const StatusBadge = ({ status }: { status: string }) => (
  <span
    className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold ${
      status === 'present' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`}
  >
    {status === 'present' ? 'Present' : 'Absent'}
  </span>
);
