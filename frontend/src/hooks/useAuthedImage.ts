import { useEffect, useState } from 'react';
import { apiBlob } from '../api/client';

/** Load a protected image through fetch (with the JWT) and expose it as an object URL. */
export function useAuthedImage(url: string | null | undefined) {
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!url);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    if (!url) {
      setSrc(null);
      setLoading(false);
      setError(false);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setError(false);
    apiBlob(url)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url]);

  return { src, loading, error };
}
