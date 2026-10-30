import { useEffect, useMemo, useRef, useState } from 'react';
import { Plus, UploadCloud, X } from 'lucide-react';

interface Props {
  files: File[];
  onChange: (files: File[]) => void;
}

/** Pick one or more class photos (click or drop). Photos stay in the list until removed. */
export const PhotoPicker = ({ files, onChange }: Props) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  const add = (list: FileList | null) => {
    if (list && list.length) onChange([...files, ...Array.from(list)]);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}
      className={`border-2 border-dashed rounded-xl p-4 ${over ? 'border-indigo-500 bg-indigo-50/50' : 'border-gray-300'}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => { add(e.target.files); e.target.value = ''; }}
      />

      {files.length === 0 ? (
        <div onClick={() => inputRef.current?.click()} className="p-6 text-center cursor-pointer">
          <UploadCloud className="w-8 h-8 mx-auto text-indigo-600 mb-2" />
          <p className="text-sm font-semibold text-gray-800">Click or drop the class photo(s) here</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {previews.map((src, i) => (
            <div key={src} className="relative aspect-video rounded-lg overflow-hidden border border-gray-200 bg-black/5">
              <img src={src} alt={`Class photo ${i + 1}`} className="w-full h-full object-cover" />
              <button
                type="button"
                onClick={() => onChange(files.filter((_, j) => j !== i))}
                className="absolute top-1.5 right-1.5 bg-white/90 hover:bg-white rounded-full p-1 shadow"
                title="Remove photo"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="aspect-video rounded-lg border border-dashed border-gray-300 text-gray-500 hover:border-indigo-400 hover:text-indigo-600 flex flex-col items-center justify-center text-xs font-medium"
          >
            <Plus className="w-5 h-5 mb-1" />
            Add another photo
          </button>
        </div>
      )}
    </div>
  );
};
