import { Trophy, Zap, AlertTriangle } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

function BarSegment({ label, value, color, maxWidth }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-arbiter-text-dim font-mono">{label}</span>
        <span className={`font-semibold ${color}`}>{value > 0 ? `+${value}` : value}</span>
      </div>
      <div className="h-2.5 bg-arbiter-bg overflow-hidden">
        <div
          className={`h-full transition-all duration-700 ${
            value >= 0 ? 'bg-arbiter-red' : 'bg-arbiter-red-bright'
          }`}
          style={{ width: `${Math.min(Math.abs(maxWidth), 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function ScorePanel() {
  const { runData } = useAgentStore();
  if (!runData) return null;

  const { score } = runData;
  const pct = Math.min((score.final / 110) * 100, 100);

  // Color based on score
  let ringColor = 'text-arbiter-green';
  let bgRing = 'stroke-[#2EA043]';
  if (score.final < 70) { ringColor = 'text-arbiter-red-bright'; bgRing = 'stroke-[#C43A15]'; }
  else if (score.final < 90) { ringColor = 'text-arbiter-amber'; bgRing = 'stroke-[#D29922]'; }

  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="animate-slide-in bg-arbiter-surface border border-arbiter-border p-6 shadow-lg">
      <h2 className="text-lg font-bold text-arbiter-text mb-5 flex items-center gap-2 font-mono">
        <Trophy className="w-5 h-5 text-arbiter-amber" />
        Score Breakdown
      </h2>

      <div className="flex flex-col sm:flex-row items-center gap-8">
        {/* Circular progress */}
        <div className="relative w-36 h-36 shrink-0">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="54" fill="none" stroke="#30363D" strokeWidth="10" />
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              className={bgRing}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              style={{ transition: 'stroke-dashoffset 1s ease-out' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-black ${ringColor}`}>{score.final}</span>
            <span className="text-xs text-arbiter-text-dim -mt-1 font-mono">/ 110</span>
          </div>
        </div>

        {/* Breakdown bars */}
        <div className="flex-1 w-full space-y-4">
          <BarSegment label="Base Score" value={score.base} color="text-arbiter-red-bright" maxWidth={100} />
          <BarSegment
            label={
              <span className="flex items-center gap-1">
                <Zap className="w-3 h-3 text-arbiter-green" /> Speed Bonus ({"<"} 5 min)
              </span>
            }
            value={score.speedBonus}
            color="text-arbiter-green"
            maxWidth={score.speedBonus > 0 ? 100 : 0}
          />
          <BarSegment
            label={
              <span className="flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-arbiter-amber" /> Efficiency Penalty (-2/commit over 20)
              </span>
            }
            value={score.efficiencyPenalty > 0 ? -score.efficiencyPenalty : 0}
            color="text-arbiter-red-bright"
            maxWidth={score.efficiencyPenalty > 0 ? (score.efficiencyPenalty / 20) * 100 : 0}
          />
        </div>
      </div>
    </div>
  );
}
