export type SequenceStage = 'report' | 'reading' | 'extracting' | 'interpreting' | 'signal';

const STEPS: { key: SequenceStage; label: string }[] = [
  { key: 'report', label: 'Report' },
  { key: 'reading', label: 'Reading' },
  { key: 'extracting', label: 'Extracting' },
  { key: 'interpreting', label: 'Interpreting' },
  { key: 'signal', label: 'AEGIS Signal' },
];

export function AnalysisSequence({ stage }: { stage: SequenceStage }) {
  const currentIndex = STEPS.findIndex((s) => s.key === stage);

  return (
    <div className="card sequence" role="status" aria-live="polite">
      {STEPS.map((step, i) => (
        <div
          key={step.key}
          className={
            i < currentIndex ? 'sequence-step done' : i === currentIndex ? 'sequence-step current' : 'sequence-step'
          }
        >
          <span className="sequence-dot" />
          <span>{step.label}</span>
        </div>
      ))}
    </div>
  );
}
