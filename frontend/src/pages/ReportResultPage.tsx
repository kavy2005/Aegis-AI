import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { AppShell } from '../components/AppShell';
import { AegisSignal } from '../components/AegisSignal';
import { ParameterList } from '../components/ParameterList';
import { StateBlock } from '../components/StateBlock';
import { Disclaimer } from '../components/Disclaimer';
import type { ReportAnalysisResponse } from '../types/api';

export function ReportResultPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ReportAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getReport(Number(id))
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : 'Could not load this report.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <AppShell>
        <StateBlock title="Loading report\u2026" />
      </AppShell>
    );
  }

  if (error || !data) {
    return (
      <AppShell>
        <StateBlock variant="error" title="Couldn't load this report" subtitle={error ?? undefined} />
      </AppShell>
    );
  }

  const abnormalParameters = data.parameters.filter((p) => p.flag === 'high' || p.flag === 'low');

  return (
    <AppShell>
      <p className="eyebrow" style={{ margin: 'var(--space-6) 0 var(--space-2)' }}>
        AEGIS interpretation
      </p>

      <div className="analysis-grid">
        <div className="col-left card report-preview">
          <p className="section-title">{data.filename ?? 'Uploaded report'}</p>
          <pre>{data.raw_text_preview || 'No extracted text available for this report.'}</pre>
        </div>

        <div className="col-right stack">
          <AegisSignal
            risk={data.risk}
            abnormalParameters={abnormalParameters}
            urgentWarning={data.explanation.urgent_warning}
          />

          <div>
            <p className="section-title">Parameters</p>
            <div className="card findings-card">
              <ParameterList parameters={data.parameters} />
            </div>
          </div>

          {data.explanation.explanation.length > 0 && (
            <div>
              <p className="section-title">Why it matters</p>
              <div className="card findings-card stack">
                {data.explanation.explanation.map((item) => (
                  <div key={item.parameter}>
                    <p className="param-label">{item.parameter}</p>
                    <p style={{ fontSize: 14, color: '#445450' }}>{item.why_it_matters}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.explanation.recommended_next_steps.length > 0 && (
            <div>
              <p className="section-title">Recommended next step</p>
              <div className="card findings-card">
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, color: '#445450' }}>
                  {data.explanation.recommended_next_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>

      <Disclaimer />
    </AppShell>
  );
}
