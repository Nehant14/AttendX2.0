import React, { useEffect, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { Thresholds } from '../api/types';

interface Props {
  sessionId: string;
  defaults: Thresholds;
  busy?: boolean;
  onApply: (values: Thresholds) => void;
}

// sessionStorage lives only as long as the tab: closing the tab drops the typed values, so the
// boxes go back to the defaults. The present/absent marks they produce are saved on the server.
const storageKey = (id: string) => `attendx:thresholds:${id}`;

function load(id: string, defaults: Thresholds): Thresholds {
  try {
    const raw = sessionStorage.getItem(storageKey(id));
    if (!raw) return defaults;
    const v = JSON.parse(raw);
    if ([v.sim_accept, v.sim_review_min, v.margin_min].every((n) => typeof n === 'number' && isFinite(n))) {
      return v as Thresholds;
    }
  } catch {
    /* storage unavailable or corrupt: fall back to defaults */
  }
  return defaults;
}

function save(id: string, values: Thresholds) {
  try {
    sessionStorage.setItem(storageKey(id), JSON.stringify(values));
  } catch {
    /* ignore */
  }
}

type Draft = Record<keyof Thresholds, string>;
const toDraft = (t: Thresholds): Draft => ({
  sim_accept: String(t.sim_accept),
  sim_review_min: String(t.sim_review_min),
  margin_min: String(t.margin_min),
});

const FIELDS: { key: keyof Thresholds; label: string; hint: string }[] = [
  { key: 'sim_accept', label: 'Present if match ≥', hint: 'Minimum similarity (0–1) to mark present' },
  { key: 'sim_review_min', label: 'Review if match ≥', hint: 'Between this and the value on the left → needs review' },
  { key: 'margin_min', label: 'Min lead over next student', hint: 'How far ahead of the next-best student the match must be' },
];

export const ThresholdPanel: React.FC<Props> = ({ sessionId, defaults, busy, onApply }) => {
  const [draft, setDraft] = useState<Draft>(() => toDraft(load(sessionId, defaults)));
  const [error, setError] = useState<string | null>(null);

  // Different session page -> load that session's tab-scoped values.
  useEffect(() => {
    setDraft(toDraft(load(sessionId, defaults)));
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const parse = (): Thresholds | null => {
    const out: Partial<Thresholds> = {};
    for (const f of FIELDS) {
      const raw = draft[f.key].trim();
      const n = Number(raw);
      if (raw === '' || !isFinite(n) || n < -1 || n > 1) {
        setError(`"${f.label}" must be a number between -1 and 1.`);
        return null;
      }
      out[f.key] = n;
    }
    const v = out as Thresholds;
    if (v.sim_review_min > v.sim_accept) {
      setError('The review value cannot be higher than the present value.');
      return null;
    }
    setError(null);
    return v;
  };

  const apply = () => {
    const v = parse();
    if (!v) return;
    save(sessionId, v);
    onApply(v);
  };

  const reset = () => {
    setDraft(toDraft(defaults));
    setError(null);
    try {
      sessionStorage.removeItem(storageKey(sessionId));
    } catch {
      /* ignore */
    }
    onApply(defaults);
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-3">
      <div className="flex items-center gap-2 text-xs font-bold text-gray-700 uppercase tracking-wider">
        <SlidersHorizontal className="w-4 h-4 text-indigo-600" />
        Match thresholds
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {FIELDS.map((f) => (
          <label key={f.key} className="block text-xs font-medium text-gray-600" title={f.hint}>
            {f.label}
            <input
              type="number"
              step="0.01"
              min={-1}
              max={1}
              inputMode="decimal"
              value={draft[f.key]}
              disabled={busy}
              onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
              onKeyDown={(e) => e.key === 'Enter' && apply()}
              aria-label={f.label}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </label>
        ))}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={apply}
          disabled={busy}
          className="px-3.5 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold shadow-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          Apply thresholds
        </button>
        <button
          onClick={reset}
          disabled={busy}
          className="px-3.5 py-2 rounded-xl border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Reset to defaults
        </button>
        <span className="text-[11px] text-gray-400">
          Marks are saved. Manually marked students are left alone. Values reset when the tab closes.
        </span>
      </div>
    </div>
  );
};
