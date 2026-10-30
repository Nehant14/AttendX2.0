export const StatCard = ({ label, value, color = 'text-gray-900' }: { label: string; value: string | number; color?: string }) => (
  <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</div>
    <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
  </div>
);
