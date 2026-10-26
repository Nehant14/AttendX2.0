import React from 'react';
import { useAuthedImage } from '../hooks/useAuthedImage';

interface Props extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  src: string | null | undefined;
}

/** <img> for protected /files/... URLs (a plain <img> cannot send the Authorization header). */
export const AuthImage: React.FC<Props> = ({ src, alt, className, ...rest }) => {
  const { src: blobUrl, loading, error } = useAuthedImage(src);
  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 text-[11px] text-gray-400 ${className || ''}`}>
        Image unavailable
      </div>
    );
  }
  if (loading || !blobUrl) {
    return <div className={`animate-pulse bg-gray-200 ${className || ''}`} aria-label="Loading image" />;
  }
  return <img src={blobUrl} alt={alt} className={className} {...rest} />;
};
