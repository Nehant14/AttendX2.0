import React, { useRef, useState } from 'react';
import { UploadCloud, Image as ImageIcon, X } from 'lucide-react';

interface Props {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
  accept?: string;
  maxSizeMb?: number;
}

export const ImageDropzone: React.FC<Props> = ({
  onFileSelect,
  selectedFile,
  accept = 'image/jpeg,image/png,image/webp',
  maxSizeMb = 25,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (file.size > maxSizeMb * 1024 * 1024) {
      alert(`File is too large. Maximum size is ${maxSizeMb}MB.`);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const clearSelection = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    onFileSelect(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div className="w-full">
      {!selectedFile ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-50/50'
              : 'border-gray-300 hover:border-gray-400 bg-white'
          }`}
        >
          <input
            type="file"
            ref={inputRef}
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            accept={accept}
            className="hidden"
          />
          <div className="mx-auto w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 mb-3">
            <UploadCloud className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-gray-800">
            Click to upload or drag and drop class photo
          </p>
          <p className="text-xs text-gray-500 mt-1">JPEG, PNG, or WebP (max {maxSizeMb}MB)</p>
        </div>
      ) : (
        <div className="relative rounded-xl overflow-hidden border border-gray-200 bg-black/5">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Classroom preview"
              className="w-full max-h-[450px] object-contain mx-auto"
            />
          ) : (
            <div className="p-8 text-center flex flex-col items-center">
              <ImageIcon className="w-10 h-10 text-gray-400 mb-2" />
              <p className="text-sm font-medium text-gray-700">{selectedFile.name}</p>
            </div>
          )}
          <button
            onClick={clearSelection}
            className="absolute top-3 right-3 bg-white/90 hover:bg-white text-gray-700 rounded-full p-1.5 shadow-md transition-colors"
            title="Remove photo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
