import RadarChart from './RadarChart';
import useAgentStore from '../store/useAgentStore';

export default function PerformanceMetrics() {
  const { performance } = useAgentStore();

  return (
    <div className="bg-arbiter-surface border border-arbiter-border overflow-hidden flex flex-col h-full min-h-[340px]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-arbiter-border">
        <h3 className="text-[15px] font-bold text-arbiter-text font-mono">Performance Metrics</h3>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-arbiter-green" />
          <span className="text-[11px] font-semibold text-arbiter-text-dim tracking-wider font-mono">CURRENT</span>
        </div>
      </div>

      {/* Radar Chart */}
      <div className="flex-1 flex items-center justify-center px-4 py-3">
        <RadarChart values={performance} />
      </div>

      {/* Bottom Scores */}
      <div className="grid grid-cols-3 border-t border-arbiter-border divide-x divide-arbiter-border">
        {[
          { label: 'SPEED', value: performance.speed, color: 'text-arbiter-red-bright' },
          { label: 'EFFICIENCY', value: performance.efficiency, color: 'text-arbiter-amber' },
          { label: 'ACCURACY', value: performance.accuracy, color: 'text-arbiter-green' },
        ].map((m) => (
          <div key={m.label} className="text-center py-3">
            <span className="text-[9px] font-bold tracking-[0.12em] uppercase text-arbiter-text-dim block font-mono">
              {m.label}
            </span>
            <span className={`text-2xl font-black ${m.color} font-mono`}>{m.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
