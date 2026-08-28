import { levelMeta, flagArrow, parameterDisplayName } from '../lib/riskLevels';
import type { RiskAssessment, ExtractedParameter } from '../types/api';

const TICK_COUNT = 40;

interface Props {
  risk: RiskAssessment;
  abnormalParameters: ExtractedParameter[];
  urgentWarning?: string | null;
}

export function AegisSignal({ risk, abnormalParameters, urgentWarning }: Props) {
  const meta = levelMeta(risk.level);
  const litCount = Math.round((risk.score / 100) * TICK_COUNT);
  const topAbnormal = [...abnormalParameters]
    .sort((a, b) => (b.severity ?? 0) - (a.severity ?? 0))
    .slice(0, 4);

  return (
    <div
      className="signal"
      style={{ ['--signal-color' as string]: meta.color, ['--signal-color-deep' as string]: meta.colorDeep }}
      role="status"
      aria-label={`AEGIS Signal: ${meta.word}, score ${risk.score} of 100`}
    >
      <div className="signal-eyebrow">
        <span className="eyebrow">AEGIS Signal</span>
        <span className="mono" style={{ fontSize: 13, color: '#5B6864' }}>
          {risk.score}/100
        </span>
      </div>

      <h2 className="signal-word" style={{ textTransform: 'uppercase' }}>
        {meta.word}
      </h2>

      <div className="signal-bar" aria-hidden="true">
        {Array.from({ length: TICK_COUNT }, (_, i) => (
          <div
            key={i}
            className={
              i < litCount - 1 ? 'signal-tick lit' : i === litCount - 1 ? 'signal-tick lit leading' : 'signal-tick'
            }
          />
        ))}
      </div>

      <p className="signal-count">
        <strong>{String(risk.abnormal_count).padStart(2, '0')}</strong>{' '}
        {risk.abnormal_count === 1 ? 'parameter needs' : 'parameters need'} attention
      </p>

      {topAbnormal.length > 0 && (
        <ul className="signal-list">
          {topAbnormal.map((p) => (
            <li key={p.id ?? p.raw_label}>
              <span>{parameterDisplayName(p.canonical_parameter, p.raw_label)}</span>
              <span className="arrow">{flagArrow(p.flag)}</span>
            </li>
          ))}
        </ul>
      )}

      {urgentWarning && <p className="signal-urgent">{urgentWarning}</p>}
    </div>
  );
}
