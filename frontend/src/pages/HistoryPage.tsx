import { Suspense, lazy, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { AppShell } from '../components/AppShell';
import { StateBlock } from '../components/StateBlock';
import { levelMeta } from '../lib/riskLevels';
import type { HistoryPoint } from '../types/api';

const HistoryChart = lazy(() =>
  import('../components/HistoryChart').then((m) => ({ default: m.HistoryChart }))
);

export function HistoryPage() {
  const [points, setPoints] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getMyHistory()
      .then((res) => {
        if (!cancelled) setPoints([...res].reverse());
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : 'Could not load your history.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AppShell>
      <p className="eyebrow hero-eyebrow" style={{ marginTop: 'var(--space-6)' }}>
        Report history
      </p>
      <h1 className="hero-title" style={{ fontSize: 32, marginBottom: 'var(--space-6)' }}>
        What changed
      </h1>

      {loading && <StateBlock title="Loading your history\u2026" />}
      {!loading && error && <StateBlock variant="error" title="Couldn't load your history" subtitle={error} />}

      {!loading && !error && points.length === 0 && (
        <StateBlock
          title="No analysed reports yet"
          subtitle="Once you analyse a report, its risk score will appear here over time."
        />
      )}

      {!loading && !error && points.length > 0 && (
        <div className="stack">
          {points.length > 1 && (
            <div className="card chart-card">
              <Suspense fallback={<div className="state-sub">Loading chart&hellip;</div>}>
                <HistoryChart points={[...points].reverse()} />
              </Suspense>
            </div>
          )}

          <div className="card">
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {points.map((p) => {
                const meta = levelMeta(p.level);
                return (
                  <li key={p.report_id} className="param-row" style={{ padding: '0' }}>
                    <Link
                      to={`/reports/${p.report_id}`}
                      className="row-between"
                      style={{ textDecoration: 'none', color: 'inherit', padding: 'var(--space-4)' }}
                    >
                      <span>
                        <span className="mono" style={{ fontSize: 13, color: '#5B6864' }}>
                          {new Date(p.date).toLocaleDateString(undefined, {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </span>
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span className="mono" style={{ fontSize: 13 }}>
                          {p.score}/100
                        </span>
                        <span
                          className="mono"
                          style={{ fontSize: 13, fontWeight: 600, color: meta.colorDeep }}
                        >
                          {meta.short}
                        </span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </AppShell>
  );
}
