import { Suspense, lazy, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { AppShell } from '../components/AppShell';
import { ReportComparison } from '../components/ReportComparison';
import { StateBlock } from '../components/StateBlock';
import { levelMeta } from '../lib/riskLevels';
import type { HistoryPoint } from '../types/api';

const HistoryChart = lazy(() =>
  import('../components/HistoryChart').then((m) => ({ default: m.HistoryChart }))
);

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function abnormalLabel(count: number) {
  if (count === 0) return 'No values need attention';
  if (count === 1) return '1 value needs attention';
  return `${count} values need attention`;
}

export function HistoryPage() {
  const [points, setPoints] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comparisonOpen, setComparisonOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    api
      .getMyHistory()
      .then((res) => {
        if (!cancelled) {
          setPoints([...res].reverse());
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof ApiError
              ? e.message
              : 'Could not load your health history.'
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const newest = points[0];
  const previous = points[1];

  return (
    <AppShell>
      <section className="hero">
        <p className="eyebrow hero-eyebrow">Health memory</p>

        <h1 className="hero-title">Your health over time.</h1>

        <p className="hero-lede">
          AEGIS keeps your analysed reports together so you can see how your
          results change from one report to the next.
        </p>
      </section>

      {loading && (
        <StateBlock title="Loading your health history…" />
      )}

      {!loading && error && (
        <StateBlock
          variant="error"
          title="Couldn't load your health history"
          subtitle={error}
        />
      )}

      {!loading && !error && points.length === 0 && (
        <StateBlock
          title="No analysed reports yet"
          subtitle="Once you analyse a laboratory report, AEGIS will start building your health history here."
          action={{
            label: 'Analyse a report',
            onClick: () => {
              window.location.href = '/analyze';
            },
          }}
        />
      )}

      {!loading && !error && points.length > 0 && (
        <div className="stack">
          {points.length > 1 && (
            <>
              <div className="history-action-row">
                <div>
                  <p className="section-title">Compare reports</p>
                  <p className="history-action-copy">
                    See what changed between your two most recent analysed reports.
                  </p>
                </div>

                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setComparisonOpen(true)}
                >
                  Compare latest reports
                </button>
              </div>

              {comparisonOpen && newest && previous && (
                <ReportComparison
                  older={{
                    report_id: previous.report_id,
                    date: previous.date,
                    filename: previous.filename,
                  }}
                  newer={{
                    report_id: newest.report_id,
                    date: newest.date,
                    filename: newest.filename,
                  }}
                  onClose={() => setComparisonOpen(false)}
                />
              )}

              <div>
                <p className="section-title">Risk score over time</p>

                <div className="card chart-card">
                  <Suspense
                    fallback={
                      <div className="state-sub">
                        Loading chart…
                      </div>
                    }
                  >
                    <HistoryChart points={[...points].reverse()} />
                  </Suspense>
                </div>
              </div>
            </>
          )}

          <div>
            <p className="section-title">
              Your reports
            </p>

            <div className="history-timeline">
              {points.map((point, index) => {
                const meta = levelMeta(point.level);
                const isLatest = index === 0;

                return (
                  <article
                    key={point.report_id}
                    className="card history-card"
                  >
                    <div className="history-card-main">
                      <div className="history-card-copy">
                        <div className="history-card-date">
                          {formatDate(point.date)}

                          {isLatest && (
                            <span className="history-latest">
                              Latest
                            </span>
                          )}
                        </div>

                        <h2 className="history-card-title">
                          {point.filename}
                        </h2>

                        <p className="history-card-subtitle">
                          {abnormalLabel(point.abnormal_count)}
                        </p>
                      </div>

                      <div className="history-card-status">
                        <span className="mono history-score">
                          {point.score}/100
                        </span>

                        <span
                          className="mono history-risk"
                          style={{ color: meta.colorDeep }}
                        >
                          {point.risk_label || meta.short}
                        </span>
                      </div>
                    </div>

                    <div className="history-card-footer">
                      <span className="mono history-parameter-count">
                        {Object.keys(point.parameters).length} parameters
                      </span>

                      <Link
                        to={`/reports/${point.report_id}`}
                        className="history-view-link"
                      >
                        View report
                        <span aria-hidden="true">→</span>
                      </Link>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}