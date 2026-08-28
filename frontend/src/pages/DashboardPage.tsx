import { Suspense, lazy, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { AppShell } from '../components/AppShell';
import { AegisSignal } from '../components/AegisSignal';
import { ParameterList } from '../components/ParameterList';
import { StateBlock } from '../components/StateBlock';
import { Disclaimer } from '../components/Disclaimer';
import type { ReportAnalysisResponse, HistoryPoint } from '../types/api';

const HistoryChart = lazy(() =>
  import('../components/HistoryChart').then((m) => ({ default: m.HistoryChart }))
);

export function DashboardPage() {
  const [latest, setLatest] = useState<ReportAnalysisResponse | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const reports = await api.listReports();
        const hist = await api.getMyHistory();
        if (cancelled) return;
        setHistory(hist);

        if (reports.length > 0) {
          const mostRecent = reports[0];
          try {
            const analysis = await api.getReport(mostRecent.id);
            if (!cancelled) setLatest(analysis);
          } catch (e) {
            // Most recent report may not be analyzed yet -- not a page-level error.
            if (!(e instanceof ApiError && e.status === 404)) throw e;
          }
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof ApiError ? e.message : 'Could not load your dashboard.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const abnormalParameters = latest?.parameters.filter((p) => p.flag === 'high' || p.flag === 'low') ?? [];

  return (
    <AppShell>
      <section className="hero">
        <p className="eyebrow hero-eyebrow">Your health report</p>
        <h1 className="hero-title">One report. One clear picture.</h1>
        <p className="hero-lede">
          Upload a laboratory report and let AEGIS interpret the available values against reference
          ranges, in plain language.
        </p>
        <Link to="/analyze" className="btn btn-primary">
          Analyse report
        </Link>
      </section>

      {loading && <StateBlock title="Loading your dashboard\u2026" />}
      {!loading && error && <StateBlock variant="error" title="Couldn't load your dashboard" subtitle={error} />}

      {!loading && !error && (
        <div className="dashboard-grid">
          <div className="stack">
            {latest ? (
              <div>
                <p className="section-title">Recent findings</p>
                <div className="card findings-card">
                  <ParameterList parameters={latest.parameters} />
                </div>
              </div>
            ) : (
              <StateBlock
                title="No reports yet"
                subtitle="Upload your first laboratory report to see your AEGIS Signal here."
                action={{ label: 'Analyse a report', onClick: () => (window.location.href = '/analyze') }}
              />
            )}

            {history.length > 1 && (
              <div>
                <p className="section-title">What changed</p>
                <div className="card chart-card">
                  <Suspense fallback={<div className="state-sub">Loading chart&hellip;</div>}>
                    <HistoryChart points={history} />
                  </Suspense>
                </div>
              </div>
            )}
          </div>

          <div>
            {latest ? (
              <AegisSignal
                risk={latest.risk}
                abnormalParameters={abnormalParameters}
                urgentWarning={latest.explanation.urgent_warning}
              />
            ) : (
              <div className="card" style={{ padding: 'var(--space-6)' }}>
                <p className="eyebrow" style={{ marginBottom: 8 }}>
                  AEGIS Signal
                </p>
                <p className="state-sub">Your signal appears here once a report has been analysed.</p>
              </div>
            )}
          </div>
        </div>
      )}

      <Disclaimer />
    </AppShell>
  );
}
