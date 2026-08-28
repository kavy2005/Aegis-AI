export interface LevelMeta {
  word: string;
  short: string;
  color: string;
  colorDeep: string;
}

export const LEVEL_META: Record<number, LevelMeta> = {
  1: { word: 'Stable', short: 'Stable', color: 'var(--teal)', colorDeep: 'var(--teal-deep)' },
  2: { word: 'Low concern', short: 'Low', color: 'var(--teal)', colorDeep: 'var(--teal-deep)' },
  3: { word: 'Moderate concern', short: 'Moderate', color: 'var(--amber)', colorDeep: 'var(--amber-deep)' },
  4: { word: 'High concern', short: 'High', color: 'var(--coral)', colorDeep: 'var(--coral-deep)' },
  5: { word: 'Urgent attention', short: 'Urgent', color: 'var(--coral-deep)', colorDeep: 'var(--coral-deep)' },
};

export function levelMeta(level: number): LevelMeta {
  return LEVEL_META[level] ?? LEVEL_META[1];
}

export function flagLabel(flag?: string | null): string {
  if (flag === 'high') return 'Above reference';
  if (flag === 'low') return 'Below reference';
  if (flag === 'normal') return 'Within reference';
  return 'Reference unavailable';
}

export function flagArrow(flag?: string | null): string {
  if (flag === 'high') return '\u2191';
  if (flag === 'low') return '\u2193';
  return '';
}

export function parameterDisplayName(canonical?: string | null, rawLabel?: string): string {
  if (!canonical) return rawLabel ?? 'Unknown parameter';
  return canonical
    .split('_')
    .map((w) => (w === 'bp' ? 'BP' : w === 'hba1c' ? 'HbA1c' : w === 'ldl' || w === 'hdl' ? w.toUpperCase() : w === 'bmi' ? 'BMI' : w === 'alt' || w === 'ast' ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ');
}
