import { useEffect, useRef, useState } from 'react';
import { UploadCloud, X } from 'lucide-react';

interface Props {
  file: File | null;
  onChange: (file: File | null) => void;
}

/** Click or drop one image; shows a preview. */
export const ImageDropzone = ({ file, onChange }: Props) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  if (file && preview) {
    return (
      <div className="relative rounded-xl overflow-hidden border border-gray-200 bg-black/5">
        <img src={preview} alt="Class photo" className="w-full max-h-[450px] object-contain mx-auto" />
        <button
          type="button"
          onClick={() => onChange(null)}
          className="absolute top-3 right-3 bg-white/90 hover:bg-white rounded-full p-1.5 shadow"
          title="Remove photo"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (e.dataTransfer.files[0]) onChange(e.dataTransfer.files[0]);
      }}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer ${
        over ? 'border-indigo-500 bg-indigo-50/50' : 'border-gray-300 hover:border-gray-400'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])}
      />
      <UploadCloud className="w-8 h-8 mx-auto text-indigo-600 mb-2" />
      <p className="text-sm font-semibold text-gray-800">Click or drop the class photo here</p>
    </div>
  );
};
