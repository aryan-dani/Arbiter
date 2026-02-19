import { GitBranch, Users, Bug, Wrench, Globe } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

function Stat({ icon: Icon, label, value, color = 'text-arbiter-text' }) {
  return (
    <div className="flex items-center gap-3">
      <div className="p-2 bg-arbiter-bg border border-arbiter-border">
        <Icon className="w-4 h-4 text-arbiter-text-muted" />
      </div>
      <div>
        <p className="text-xs text-arbiter-text-dim font-mono">{label}</p>
        <p className={`text-sm font-semibold ${color}`}>{value}</p>
      </div>
    </div>
  );
}

export default function SummaryCard() {
  const { runData } = useAgentStore();
  if (!runData) return null;

  const { repoUrl, teamName, leaderName, branchName, totalFixes, totalFailures, totalCommits, totalTimeMs } = runData;
  const timeStr = `${(totalTimeMs / 60000).toFixed(1)} min`;

  return (
    <div className="animate-slide-in bg-arbiter-surface border border-arbiter-border p-6 shadow-lg">
      <h2 className="text-lg font-bold text-arbiter-text mb-5 flex items-center gap-2 font-mono">
        <Globe className="w-5 h-5 text-arbiter-red-bright" />
        Run Summary
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
        <Stat icon={Globe} label="Repository" value={repoUrl.replace('https://github.com/', '')} />
        <Stat icon={Users} label="Team" value={teamName} />
        <Stat icon={Users} label="Leader" value={leaderName} />
        <Stat icon={Bug} label="Total Failures" value={totalFailures} color={totalFailures > 0 ? 'text-arbiter-red-bright' : 'text-arbiter-green'} />
        <Stat icon={Wrench} label="Total Fixes" value={totalFixes} color="text-arbiter-green" />
        <Stat icon={GitBranch} label="Commits / Time" value={`${totalCommits} commits · ${timeStr}`} />
      </div>

      {/* Branch Name Chip */}
      <div className="flex items-center gap-2 bg-arbiter-bg px-4 py-2.5 border border-arbiter-border">
        <GitBranch className="w-4 h-4 text-arbiter-red-bright shrink-0" />
        <span className="text-xs text-arbiter-text-dim font-mono">Branch:</span>
        <code className="text-sm font-mono text-arbiter-red-bright break-all">{branchName}</code>
      </div>
    </div>
  );
}
