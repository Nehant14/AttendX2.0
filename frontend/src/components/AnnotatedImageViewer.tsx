import React, { useEffect, useRef, useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Download, Eye, Layers } from 'lucide-react';
import { downloadFile } from '../api/client';
import { useAuthedImage } from '../hooks/useAuthedImage';

interface Props {
  annotatedUrl: string | null;
  originalUrl: string | null;
}

const MIN_SCALE = 0.5;
const MAX_SCALE = 6;

export const AnnotatedImageViewer: React.FC<Props> = ({ annotatedUrl, originalUrl }) => {
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const dragStart = useRef({ x: 0, y: 0, px: 0, py: 0 });

  const activeUrl = showOriginal ? originalUrl : annotatedUrl || originalUrl;
  const { src, loading, error } = useAuthedImage(activeUrl);

  const clamp = (v: number) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, v));
  const zoomBy = (delta: number) => setScale((s) => clamp(+(s + delta).toFixed(2)));
  const reset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  // React attaches wheel listeners as passive, so preventDefault() (to stop the page from
  // scrolling while zooming) only works with a native non-passive listener.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      setScale((s) => clamp(+(s + (e.deltaY < 0 ? 0.25 : -0.25)).toFixed(2)));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // Pointer events cover mouse, touch and pen.
  const onPointerDown = (e: React.PointerEvent) => {
    if (scale <= 1) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, px: position.x, py: position.y };
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging) return;
    setPosition({
      x: dragStart.current.px + (e.clientX - dragStart.current.x),
      y: dragStart.current.py + (e.clientY - dragStart.current.y),
    });
  };
  const onPointerUp = () => setDragging(false);

  const handleDownload = async () => {
    if (!activeUrl) return;
    setDownloadError(null);
    try {
      await downloadFile(activeUrl, showOriginal ? 'classroom_original.jpg' : 'classroom_annotated.jpg');
    } catch (err: any) {
      setDownloadError(err.message || 'Download failed');
    }
  };

  const btn =
    'p-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 shadow-sm transition-colors';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3 bg-gray-50/70">
        <div className="flex items-center gap-1.5">
          <button onClick={() => zoomBy(0.25)} className={btn} title="Zoom in" aria-label="Zoom in">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={() => zoomBy(-0.25)} className={btn} title="Zoom out" aria-label="Zoom out">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button onClick={reset} className={btn} title="Reset zoom" aria-label="Reset zoom">
            <RotateCcw className="w-4 h-4" />
          </button>
          <span className="text-xs font-medium text-gray-500 ml-1">{Math.round(scale * 100)}%</span>
        </div>

        <div className="flex items-center gap-2">
          {originalUrl && annotatedUrl && (
            <button
              onClick={() => setShowOriginal((v) => !v)}
              className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                showOriginal
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {showOriginal ? (
                <>
                  <Layers className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                  Showing original
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
                  View original
                </>
              )}
            </button>
          )}
          {activeUrl && (
            <button
              onClick={handleDownload}
              className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
            >
              <Download className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
              Download
            </button>
          )}
        </div>
      </div>
      {downloadError && <div className="px-4 py-2 text-xs text-red-600 bg-red-50">{downloadError}</div>}

      <div
        ref={viewportRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        style={{ touchAction: scale > 1 ? 'none' : 'auto' }}
        className={`relative w-full h-[320px] sm:h-[450px] lg:h-[550px] bg-gray-900 overflow-hidden flex items-center justify-center select-none ${
          scale > 1 ? 'cursor-grab active:cursor-grabbing' : ''
        }`}
      >
        {error ? (
          <div className="text-gray-400 text-sm">Image could not be loaded.</div>
        ) : loading || !src ? (
          <div className="text-gray-400 text-sm animate-pulse">{activeUrl ? 'Loading image…' : 'No image available'}</div>
        ) : (
          <img
            src={src}
            alt={showOriginal ? 'Original classroom photo' : 'Annotated classroom photo'}
            draggable={false}
            style={{
              transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
              transition: dragging ? 'none' : 'transform 0.15s ease-out',
            }}
            className="max-h-full max-w-full object-contain pointer-events-none"
          />
        )}
      </div>
    </div>
  );
};
