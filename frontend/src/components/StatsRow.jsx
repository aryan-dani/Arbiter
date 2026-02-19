import { Zap, CheckCircle, Clock, Wrench } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

const STATS = [
  {
    label: 'TOTAL RUNS',
    key: 'totalRuns',
    icon: Zap,
    format: (v) => v.toLocaleString(),
    color: '#3b82f6',
  },
  {
    label: 'LAST RUN',
    key: 'successRate',
    icon: CheckCircle,
    format: (v, runData, runComplete) => {
      if (!runComplete) return 'N/A';
      return runData?.passed ? 'PASSED' : 'FAILED';
    },
    colorFn: (runData, runComplete) => {
      if (!runComplete) return 'text-arbiter-text-dim';
      return runData?.passed ? 'text-arbiter-green' : 'text-arbiter-red-bright';
    },
  },
  {
    label: 'HEAL TIME',
    key: 'avgHealTime',
    icon: Clock,
    format: (v) => (v === 'N/A' ? '—' : v),
    color: '#f59e0b',
  },
  {
    label: 'FIXES APPLIED',
    key: 'totalFixes',
    icon: Wrench,
    format: (v) => (v == null ? '0' : String(v)),
    color: '#8b5cf6',
  },
];

export default function StatsRow() {
  const { stats, runData, runComplete } = useAgentStore();

  const values = {
    totalRuns: stats.totalRuns,
    successRate: stats.successRate,
    avgHealTime: stats.avgHealTime,
    totalFixes: runData?.totalFixes ?? 0,
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 px-5 py-4">
      {STATS.map((s) => {
        const raw = values[s.key];
        const displayValue = s.format(raw, runData, runComplete);
        const colorClass = s.colorFn ? s.colorFn(runData, runComplete) : 'text-arbiter-text';

        return (
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

            {/* Value */}
            <div className="flex items-end gap-2">
              <span className={`text-2xl lg:text-3xl font-black font-mono tracking-tight ${colorClass}`}>
                {displayValue}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
