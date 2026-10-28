import { useEffect, useState } from 'react';
import { apiBlob } from '../api/client';

/** Load a protected image through fetch (with the JWT) and expose it as an object URL. */
export function useAuthedImage(url: string | null | undefined) {
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!url);
  const [error, setError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!url) {
      setSrc(null);
      setLoading(false);
      setError(false);
      setErrorMessage(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setError(false);
    setErrorMessage(null);
    apiBlob(url)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((err: any) => {
        if (cancelled) return;
        setError(true);
        const status = typeof err?.status === 'number' && err.status > 0 ? `HTTP ${err.status}` : '';
        setErrorMessage([status, err?.message].filter(Boolean).join(' - ') || 'Unknown error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url]);

  return { src, loading, error, errorMessage };
}
