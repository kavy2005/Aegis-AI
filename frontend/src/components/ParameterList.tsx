import { flagLabel, parameterDisplayName } from '../lib/riskLevels';
import type { ExtractedParameter } from '../types/api';

function ParamRow({ p }: { p: ExtractedParameter }) {
  const flag = p.flag ?? 'unrecognized';
  return (
    <div className="param-row">
      <div className="param-label">{parameterDisplayName(p.canonical_parameter, p.raw_label)}</div>
      <div className="param-value-row">
        <span className="param-value">{p.value ?? '\u2014'}</span>
        {p.unit && <span className="param-unit">{p.unit}</span>}
      </div>
      <div className={`param-status ${flag}`}>{flagLabel(p.flag)}</div>
    </div>
  );
}

export function ParameterList({ parameters }: { parameters: ExtractedParameter[] }) {
  const abnormal = parameters.filter((p) => p.flag === 'high' || p.flag === 'low');
  const normal = parameters.filter((p) => p.flag === 'normal');
  const unrecognized = parameters.filter((p) => !p.flag || p.flag === 'unrecognized');

  return (
    <div className="stack">
      {abnormal.length > 0 && (
        <div>
          <p className="section-title">Needs attention</p>
          <div className="param-grid">
            {abnormal.map((p) => (
              <ParamRow key={p.id ?? p.raw_label} p={p} />
            ))}
          </div>
        </div>
      )}
      {normal.length > 0 && (
        <div>
          <p className="section-title">Within reference</p>
          <div className="param-grid">
            {normal.map((p) => (
              <ParamRow key={p.id ?? p.raw_label} p={p} />
            ))}
          </div>
        </div>
      )}
      {unrecognized.length > 0 && (
        <div>
          <p className="section-title">Not matched to a known parameter</p>
          <div className="param-grid">
            {unrecognized.map((p) => (
              <ParamRow key={p.id ?? p.raw_label} p={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
