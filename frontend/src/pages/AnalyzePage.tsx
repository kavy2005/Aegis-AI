import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { AppShell } from '../components/AppShell';
import { UploadDropzone } from '../components/UploadDropzone';
import { AnalysisSequence, type SequenceStage } from '../components/AnalysisSequence';
import { StateBlock } from '../components/StateBlock';
import { withMinDuration } from '../lib/timing';

export function AnalyzePage() {
  const navigate = useNavigate();
  const [stage, setStage] = useState<SequenceStage | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAnalysis(file: File) {
    setError(null);
    setStage('reading');
    try {
      const upload = await withMinDuration(api.uploadReport(file), 700);

      setStage('extracting');
      await withMinDuration(Promise.resolve(upload), 700);

      setStage('interpreting');
      const analysis = await withMinDuration(api.analyzeReport(upload.report_id), 900);

      setStage('signal');
      await withMinDuration(Promise.resolve(analysis), 500);

      navigate(`/reports/${upload.report_id}`);
    } catch (e) {
      setStage(null);
      setError(
        e instanceof ApiError
          ? e.message
          : 'Something went wrong while analysing this report. Try again.'
      );
    }
  }

  return (
    <AppShell>
      <p className="eyebrow hero-eyebrow" style={{ marginTop: 'var(--space-6)' }}>
        Analyse report
      </p>
      <h1 className="hero-title" style={{ fontSize: 32, marginBottom: 'var(--space-6)' }}>
        Upload a report
      </h1>

      {!stage && (
        <div className="stack">
          <UploadDropzone onFileSelected={runAnalysis} />
          {error && (
            <StateBlock
              variant="error"
              title="Couldn't analyse this report"
              subtitle={error}
            />
          )}
        </div>
      )}

      {stage && <AnalysisSequence stage={stage} />}
    </AppShell>
  );
}
