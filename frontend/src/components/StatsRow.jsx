import { TrendingUp, TrendingDown, Zap, CheckCircle, Clock, Users } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

/* Tiny SVG sparkline */
function Sparkline({ data, color }) {
  const h = 24;
  const w = 60;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(' ');
  return (
    <svg width={w} height={h} className="opacity-60">
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  );
}

const STATS = [
  {
    label: 'TOTAL RUNS',
    key: 'totalRuns',
    icon: Zap,
    format: (v) => v.toLocaleString(),
    change: '+12%',
    up: true,
    sparkData: [20, 35, 30, 45, 40, 55, 50, 65, 62, 72, 68, 80],
    color: '#3b82f6',
  },
  {
    label: 'SUCCESS RATE',
    key: 'successRate',
    icon: CheckCircle,
    format: (v) => `${v}%`,
    change: '+2.3%',
    up: true,
    sparkData: [60, 65, 63, 70, 72, 68, 75, 78, 80, 82, 85, 88],
    color: '#22c55e',
  },
  {
    label: 'AVG HEAL TIME',
    key: 'avgHealTime',
    icon: Clock,
    format: (v) => v,
    change: '-18%',
    up: false,
    sparkData: [80, 75, 78, 70, 65, 60, 58, 55, 52, 48, 45, 40],
    color: '#f59e0b',
  },
  {
    label: 'ACTIVE AGENTS',
    key: 'activeAgents',
    icon: Users,
    format: (v) => v,
    change: '',
    up: true,
    sparkData: [4, 6, 5, 7, 8, 6, 7, 9, 8, 10, 8, 8],
    color: '#8b5cf6',
  },
];

export default function StatsRow() {
  const { stats } = useAgentStore();

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 px-5 py-4">
      {STATS.map((s) => (
        <div
          key={s.key}
          className="bg-arbiter-surface border border-arbiter-border px-4 py-4 flex flex-col gap-2"
        >
          {/* Header */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold tracking-[0.12em] uppercase text-arbiter-text-dim font-mono">
              {s.label}
            </span>
            <s.icon className="w-4 h-4 text-arbiter-text-dim" />
          </div>

          {/* Value row */}
          <div className="flex items-end justify-between gap-2">
            <span className="text-2xl lg:text-3xl font-black text-arbiter-text font-mono tracking-tight">
              {s.format(stats[s.key])}
            </span>
            <Sparkline data={s.sparkData} color={s.color} />
          </div>

          {/* Change badge */}
          {s.change && (
            <div className="flex items-center gap-1">
              {s.up ? (
                <TrendingUp className="w-3 h-3 text-arbiter-green" />
              ) : (
                <TrendingDown className="w-3 h-3 text-arbiter-green" />
              )}
              <span className="text-[11px] text-arbiter-green font-medium">{s.change}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
