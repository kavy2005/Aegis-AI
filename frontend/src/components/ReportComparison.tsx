import { useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../api/client';
import { levelMeta } from '../lib/riskLevels';
import type { ExtractedParameter, ReportAnalysisResponse } from '../types/api';

interface ReportComparisonProps {
  older: {
    report_id: number;
    date: string;
    filename: string;
  };
  newer: {
    report_id: number;
    date: string;
    filename: string;
  };
  onClose: () => void;
}

type ChangeKind =
  | 'improved'
  | 'worsened'
  | 'new'
  | 'resolved'
  | 'still_abnormal'
  | 'stable';

interface ComparisonRow {
  parameter: string;
  older: ExtractedParameter | null;
  newer: ExtractedParameter | null;
  change: number | null;
  kind: ChangeKind;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function displayName(parameter: ExtractedParameter | null) {
  return parameter?.canonical_parameter || parameter?.raw_label || 'Unknown parameter';
}

function formatValue(parameter: ExtractedParameter | null) {
  if (!parameter || parameter.value === null || parameter.value === undefined) {
    return '—';
  }

  return `${parameter.value}${parameter.unit ? ` ${parameter.unit}` : ''}`;
}

function getFlag(parameter: ExtractedParameter | null) {
  if (!parameter) return null;
  return parameter.flag === 'high' || parameter.flag === 'low'
    ? parameter.flag
    : null;
}

function classifyChange(
  older: ExtractedParameter | null,
  newer: ExtractedParameter | null
): ChangeKind {
  const olderFlag = getFlag(older);
  const newerFlag = getFlag(newer);

  if (!older && newer) {
    return newerFlag ? 'new' : 'stable';
  }

  if (older && !newer) {
    return olderFlag ? 'resolved' : 'stable';
  }

  if (olderFlag && !newerFlag) {
    return 'resolved';
  }

  if (!olderFlag && newerFlag) {
    return 'new';
  }

  if (olderFlag && newerFlag) {
    if (olderFlag === newerFlag) {
      return 'still_abnormal';
    }

    return 'still_abnormal';
  }

  return 'stable';
}

function kindLabel(kind: ChangeKind) {
  switch (kind) {
    case 'improved':
      return 'Improved';
    case 'worsened':
      return 'Worsened';
    case 'new':
      return 'New';
    case 'resolved':
      return 'Resolved';
    case 'still_abnormal':
      return 'Still needs attention';
    default:
      return 'Stable';
  }
}

function kindClass(kind: ChangeKind) {
  return `comparison-kind comparison-kind-${kind}`;
}

export function ReportComparison({
  older,
  newer,
  onClose,
}: ReportComparisonProps) {
  const [olderReport, setOlderReport] = useState<ReportAnalysisResponse | null>(null);
  const [newerReport, setNewerReport] = useState<ReportAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const [olderResult, newerResult] = await Promise.all([
          api.getReport(older.report_id),
          api.getReport(newer.report_id),
        ]);

        if (cancelled) return;

        setOlderReport(olderResult);
        setNewerReport(newerResult);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError
              ? e.message
              : 'Could not load the reports for comparison.'
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [older.report_id, newer.report_id]);

  const comparison = useMemo<ComparisonRow[]>(() => {
    if (!olderReport || !newerReport) return [];

    const olderMap = new Map(
      olderReport.parameters
        .filter((p) => p.canonical_parameter)
        .map((p) => [p.canonical_parameter as string, p])
    );

    const newerMap = new Map(
      newerReport.parameters
        .filter((p) => p.canonical_parameter)
        .map((p) => [p.canonical_parameter as string, p])
    );

    const names = new Set([
      ...olderMap.keys(),
      ...newerMap.keys(),
    ]);

    return Array.from(names)
      .map((parameter) => {
        const olderParameter = olderMap.get(parameter) ?? null;
        const newerParameter = newerMap.get(parameter) ?? null;

        const change =
          olderParameter?.value !== null &&
          olderParameter?.value !== undefined &&
          newerParameter?.value !== null &&
          newerParameter?.value !== undefined
            ? newerParameter.value - olderParameter.value
            : null;

        return {
          parameter,
          older: olderParameter,
          newer: newerParameter,
          change,
          kind: classifyChange(olderParameter, newerParameter),
        };
      })
      .filter((row) => row.kind !== 'stable' || row.change !== null)
      .sort((a, b) => {
        const order: Record<ChangeKind, number> = {
          improved: 0,
          worsened: 1,
          new: 2,
          resolved: 3,
          still_abnormal: 4,
          stable: 5,
        };

        return order[a.kind] - order[b.kind];
      });
  }, [olderReport, newerReport]);

  if (loading) {
    return (
      <div className="comparison-panel card">
        <div className="comparison-header">
          <div>
            <p className="eyebrow">Report comparison</p>
            <h2 className="comparison-title">Loading comparison…</h2>
          </div>

          <button
            type="button"
            className="comparison-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  if (error || !olderReport || !newerReport) {
    return (
      <div className="comparison-panel card">
        <div className="comparison-header">
          <div>
            <p className="eyebrow">Report comparison</p>
            <h2 className="comparison-title">Couldn't compare reports</h2>
          </div>

          <button
            type="button"
            className="comparison-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <p className="state-sub">
          {error || 'The selected reports could not be loaded.'}
        </p>
      </div>
    );
  }

  const scoreChange = newerReport.risk.score - olderReport.risk.score;
  const abnormalChange =
    newerReport.risk.abnormal_count - olderReport.risk.abnormal_count;

  const olderMeta = levelMeta(olderReport.risk.level);
  const newerMeta = levelMeta(newerReport.risk.level);

  const meaningfulRows = comparison.filter(
    (row) => row.kind !== 'stable'
  );

  return (
    <section className="comparison-panel card">
      <div className="comparison-header">
        <div>
          <p className="eyebrow">Report comparison</p>
          <h2 className="comparison-title">
            What changed
          </h2>
          <p className="comparison-intro">
            A side-by-side view of the available results in these two reports.
          </p>
        </div>

        <button
          type="button"
          className="comparison-close"
          onClick={onClose}
        >
          Close
        </button>
      </div>

      <div className="comparison-reports">
        <div className="comparison-report">
          <span className="comparison-report-label">
            Older report
          </span>
          <strong>{older.filename}</strong>
          <span>{formatDate(older.date)}</span>
        </div>

        <div className="comparison-arrow" aria-hidden="true">
          →
        </div>

        <div className="comparison-report comparison-report-newer">
          <span className="comparison-report-label">
            Newer report
          </span>
          <strong>{newer.filename}</strong>
          <span>{formatDate(newer.date)}</span>
        </div>
      </div>

      <div className="comparison-summary">
        <div className="comparison-summary-item">
          <span className="comparison-summary-label">
            AEGIS Signal
          </span>

          <div className="comparison-score-pair">
            <strong>{olderReport.risk.score}/100</strong>
            <span>→</span>
            <strong>{newerReport.risk.score}/100</strong>
          </div>

          <span
            className={`comparison-delta ${
              scoreChange < 0
                ? 'comparison-delta-positive'
                : scoreChange > 0
                  ? 'comparison-delta-negative'
                  : ''
            }`}
          >
            {scoreChange > 0 ? '+' : ''}
            {scoreChange} points
          </span>
        </div>

        <div className="comparison-summary-item">
          <span className="comparison-summary-label">
            Values needing attention
          </span>

          <div className="comparison-score-pair">
            <strong>{olderReport.risk.abnormal_count}</strong>
            <span>→</span>
            <strong>{newerReport.risk.abnormal_count}</strong>
          </div>

          <span className="comparison-delta">
            {abnormalChange > 0 ? '+' : ''}
            {abnormalChange}
          </span>
        </div>

        <div className="comparison-summary-item">
          <span className="comparison-summary-label">
            Risk level
          </span>

          <div className="comparison-level-pair">
            <strong style={{ color: olderMeta.colorDeep }}>
              {olderReport.risk.label}
            </strong>
            <span>→</span>
            <strong style={{ color: newerMeta.colorDeep }}>
              {newerReport.risk.label}
            </strong>
          </div>
        </div>
      </div>

      <div className="comparison-section">
        <div className="comparison-section-heading">
          <div>
            <p className="section-title">
              Changes in results
            </p>

            <p className="comparison-section-subtitle">
              Showing parameters that changed status or value between reports.
            </p>
          </div>

          <span className="mono comparison-count">
            {meaningfulRows.length} changes
          </span>
        </div>

        {meaningfulRows.length === 0 ? (
          <div className="comparison-empty">
            No meaningful changes were found in the available matched parameters.
          </div>
        ) : (
          <div className="comparison-rows">
            {meaningfulRows.map((row) => (
              <div
                key={row.parameter}
                className="comparison-row"
              >
                <div className="comparison-row-main">
                  <strong>
                    {displayName(row.newer || row.older)}
                  </strong>

                  <span className={kindClass(row.kind)}>
                    {kindLabel(row.kind)}
                  </span>
                </div>

                <div className="comparison-values">
                  <span>
                    {formatValue(row.older)}
                  </span>

                  <span aria-hidden="true">
                    →
                  </span>

                  <span>
                    {formatValue(row.newer)}
                  </span>

                  {row.change !== null && (
                    <span className="mono comparison-change">
                      {row.change > 0 ? '+' : ''}
                      {row.change}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="comparison-note">
        Comparison describes changes in the available report data. A change in
        a value or flag does not by itself establish a diagnosis or explain its
        cause.
      </p>
    </section>
  );
}
