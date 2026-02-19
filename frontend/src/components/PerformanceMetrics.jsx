import RadarChart from './RadarChart';
import useAgentStore from '../store/useAgentStore';

export default function PerformanceMetrics() {
  const { performance, runData, runComplete } = useAgentStore();

  const score = runData?.score ?? null;

  const scoreItems = [
    {
      label: 'BASE',
      value: score ? score.base : '—',
      color: 'text-arbiter-text',
      title: 'Base Score',
    },
    {
      label: 'BONUS',
      value: score ? `+${score.speedBonus}` : '—',
      color: score?.speedBonus > 0 ? 'text-arbiter-green' : 'text-arbiter-text-dim',
      title: 'Speed Bonus',
    },
    {
      label: 'PENALTY',
      value: score ? `-${score.efficiencyPenalty}` : '—',
      color: score?.efficiencyPenalty > 0 ? 'text-arbiter-red-bright' : 'text-arbiter-text-dim',
      title: 'Efficiency Penalty',
    },
  ];

  return (
    <div className="bg-arbiter-surface border border-arbiter-border overflow-hidden flex flex-col h-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-arbiter-border">
        <h3 className="text-[15px] font-bold text-arbiter-text font-mono">Performance Metrics</h3>
        <div className="flex items-center gap-1.5">
          {runComplete ? (
            <>
              <span className={`w-2 h-2 rounded-full ${runData?.passed ? 'bg-arbiter-green' : 'bg-arbiter-red-bright'}`} />
              <span className="text-[11px] font-semibold text-arbiter-text-dim tracking-wider font-mono">
                {runData?.passed ? 'PASSED' : 'FAILED'}
              </span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-arbiter-text-dim/40" />
              <span className="text-[11px] font-semibold text-arbiter-text-dim tracking-wider font-mono">IDLE</span>
            </>
          )}
        </div>
      </div>

      {/* Radar Chart */}
      <div className="flex-1 flex items-center justify-center px-4 py-3">
        <RadarChart values={performance} />
      </div>

      {/* Score Breakdown — real data from backend */}
      <div className="border-t border-arbiter-border">
        <div className="px-5 py-1.5">
          <span className="text-[9px] font-bold tracking-[0.12em] uppercase text-arbiter-text-dim font-mono">
            Judge Score Breakdown
          </span>
        </div>
        <div className="grid grid-cols-3 divide-x divide-arbiter-border border-t border-arbiter-border">
          {scoreItems.map((m) => (
            <div key={m.label} className="text-center py-3 group relative">
              <span className="text-[9px] font-bold tracking-[0.12em] uppercase text-arbiter-text-dim block font-mono">
                {m.label}
              </span>
              <span className={`text-2xl font-black ${m.color} font-mono`}>
                {m.value}
              </span>
              {/* Tooltip */}
              <span className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-arbiter-bg border border-arbiter-border text-[10px] font-mono text-arbiter-text whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                {m.title}
              </span>
            </div>
          ))}
        </div>
        {/* Final score */}
        {runComplete && score && (
          <div className="flex items-center justify-between px-5 py-2 border-t border-arbiter-border bg-arbiter-bg/50">
            <span className="text-[10px] font-bold tracking-[0.12em] uppercase text-arbiter-text-dim font-mono">
              FINAL SCORE
            </span>
            <span className="text-xl font-black text-arbiter-text font-mono">
              {score.final}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
