import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { HistoryPoint } from '../types/api';

export function HistoryChart({ points }: { points: HistoryPoint[] }) {
  const data = points.map((p) => ({
    date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    score: p.score,
    level: p.level,
  }));

  return (
    <div style={{ width: '100%', height: 220 }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#315C57" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#315C57" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#E8ECE7" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11, fill: '#5B6864' }}
            axisLine={{ stroke: '#E8ECE7' }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11, fill: '#5B6864' }}
            axisLine={false}
            tickLine={false}
            width={32}
          />
          <Tooltip
            contentStyle={{
              fontFamily: 'IBM Plex Mono',
              fontSize: 12,
              border: '1px solid #E8ECE7',
              borderRadius: 6,
            }}
            formatter={(value) => [`${value}/100`, 'Score']}
          />
          <Area type="monotone" dataKey="score" stroke="#315C57" strokeWidth={2} fill="url(#scoreFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
