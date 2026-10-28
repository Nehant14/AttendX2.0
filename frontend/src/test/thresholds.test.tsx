import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThresholdPanel } from '../components/ThresholdPanel';

const defaults = { sim_accept: 0.45, sim_review_min: 0.35, margin_min: 0.05 };

describe('ThresholdPanel', () => {
  beforeEach(() => sessionStorage.clear());

  it('shows the defaults and sends edited values on Apply', () => {
    const onApply = vi.fn();
    render(<ThresholdPanel sessionId="7" defaults={defaults} onApply={onApply} />);
    expect((screen.getByLabelText('Present if match ≥') as HTMLInputElement).value).toBe('0.45');
    fireEvent.change(screen.getByLabelText('Present if match ≥'), { target: { value: '0.6' } });
    fireEvent.click(screen.getByText('Apply thresholds'));
    expect(onApply).toHaveBeenCalledWith({ sim_accept: 0.6, sim_review_min: 0.35, margin_min: 0.05 });
  });

  it('keeps values for this tab only (sessionStorage), defaults when it is a fresh tab', () => {
    const { unmount } = render(<ThresholdPanel sessionId="7" defaults={defaults} onApply={() => {}} />);
    fireEvent.change(screen.getByLabelText('Present if match ≥'), { target: { value: '0.7' } });
    fireEvent.click(screen.getByText('Apply thresholds'));
    unmount();
    render(<ThresholdPanel sessionId="7" defaults={defaults} onApply={() => {}} />);
    expect((screen.getByLabelText('Present if match ≥') as HTMLInputElement).value).toBe('0.7');
    // Closing the tab clears sessionStorage; simulate that.
    sessionStorage.clear();
    const fresh = render(<ThresholdPanel sessionId="7" defaults={defaults} onApply={() => {}} />);
    const boxes = fresh.getAllByLabelText('Present if match ≥');
    expect((boxes[boxes.length - 1] as HTMLInputElement).value).toBe('0.45');
  });

  it('rejects review > present and out-of-range values', () => {
    const onApply = vi.fn();
    render(<ThresholdPanel sessionId="7" defaults={defaults} onApply={onApply} />);
    fireEvent.change(screen.getByLabelText('Review if match ≥'), { target: { value: '0.9' } });
    fireEvent.click(screen.getByText('Apply thresholds'));
    expect(screen.getByText(/cannot be higher/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Review if match ≥'), { target: { value: '2' } });
    fireEvent.click(screen.getByText('Apply thresholds'));
    expect(onApply).not.toHaveBeenCalled();
  });
});
