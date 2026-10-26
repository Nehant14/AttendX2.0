import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// jsdom has no object-URL support
if (!URL.createObjectURL) {
  (URL as any).createObjectURL = vi.fn(() => 'blob:mock-url');
  (URL as any).revokeObjectURL = vi.fn();
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});
