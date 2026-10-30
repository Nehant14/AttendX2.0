import { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

/** The class photo with the detected faces boxed. Zoom in to check small faces. */
export const ImageViewer = ({ src }: { src: string | null }) => {
  const [scale, setScale] = useState(1);
  const btn = 'p-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-1.5 bg-gray-50/70">
        <button onClick={() => setScale((s) => Math.min(6, s + 0.5))} className={btn} title="Zoom in">
          <ZoomIn className="w-4 h-4" />
        </button>
        <button onClick={() => setScale((s) => Math.max(1, s - 0.5))} className={btn} title="Zoom out">
          <ZoomOut className="w-4 h-4" />
        </button>
        <button onClick={() => setScale(1)} className={btn} title="Reset">
          <RotateCcw className="w-4 h-4" />
        </button>
        <span className="text-xs text-gray-500 ml-1">{Math.round(scale * 100)}%</span>
      </div>
      <div className="h-[320px] sm:h-[450px] lg:h-[550px] bg-gray-900 overflow-auto">
        {src ? (
          <img
            src={src}
            alt="Class photo with detected faces"
            style={{ width: `${scale * 100}%`, maxWidth: 'none' }}
            className="block mx-auto"
          />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm">No image</div>
        )}
      </div>
    </div>
  );
};
