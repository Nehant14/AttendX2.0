import React from 'react';

interface Props {
  status: 'present' | 'absent' | 'needs_review' | 'ready' | 'not_ready' | string;
  className?: string;
}

export const StatusBadge: React.FC<Props> = ({ status, className = '' }) => {
  switch (status) {
    case 'present':
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800 ${className}`}>
          Present
        </span>
      );
    case 'absent':
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 ${className}`}>
          Absent
        </span>
      );
    case 'needs_review':
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 ${className}`}>
          Needs Review
        </span>
      );
    case 'ready':
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 ${className}`}>
          Ready
        </span>
      );
    case 'not_ready':
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 ${className}`}>
          Need Photos
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 ${className}`}>
          {status}
        </span>
      );
  }
};
