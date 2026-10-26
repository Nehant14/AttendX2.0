import React, { useRef, useState } from 'react';
import { Upload, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
import { apiFetch } from '../api/client';
import { PhotoUploadResponse } from '../api/types';

interface Props {
  studentId: number;
  onUploaded: () => void;
}

export const EnrollmentPhotoUploader: React.FC<Props> = ({ studentId, onUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<PhotoUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList) => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await apiFetch<PhotoUploadResponse>(`/api/students/${studentId}/photos`, {
        method: 'POST',
        body: formData,
      });
      setResult(res);
      onUploaded();
    } catch (err: any) {
      setError(err.message || 'Failed to upload photos.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-2">
        Upload Enrollment Photos
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Upload 3 to 15 clear frontal photos of the student under varied lighting and angles.
      </p>

      <div
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 hover:border-indigo-400 bg-gray-50/50 hover:bg-indigo-50/30 rounded-xl p-6 text-center cursor-pointer transition-colors"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
          className="hidden"
        />
        <Upload className="w-8 h-8 text-indigo-500 mx-auto mb-2" />
        <span className="text-sm font-semibold text-gray-700">
          {uploading ? 'Processing photos with face detection...' : 'Select or drop face photos here'}
        </span>
        <p className="text-xs text-gray-400 mt-1">JPEG, PNG, WebP (multiple allowed)</p>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center text-xs text-red-700">
          <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          {result.warnings.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 space-y-1">
              <div className="font-semibold flex items-center">
                <AlertCircle className="w-4 h-4 mr-1 text-amber-600" />
                Duplicate Identity Warnings:
              </div>
              {result.warnings.map((w, idx) => (
                <div key={idx} className="ml-5">
                  &bull; {w}
                </div>
              ))}
            </div>
          )}

          <div className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
            {result.results.map((r, i) => (
              <div
                key={i}
                className={`p-3 flex items-start gap-2.5 text-xs ${
                  r.accepted ? 'bg-green-50/30' : 'bg-red-50/30'
                }`}
              >
                {r.accepted ? (
                  <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <div className="font-medium text-gray-800">{r.filename}</div>
                  {r.reason ? (
                    <div className="text-red-600 mt-0.5">{r.reason}</div>
                  ) : (
                    <div className="text-green-700 mt-0.5">Face detected & embedding saved</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
