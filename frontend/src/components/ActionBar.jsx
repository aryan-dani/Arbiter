import { Play, GitBranch, RotateCcw, Settings, Loader2 } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function ActionBar({ onOpenSettings }) {
  const { repoUrl, isRunning, runComplete, runAgent, reset, runData } = useAgentStore();

  const displayRepo = repoUrl
    ? repoUrl.replace(/^https?:\/\/(www\.)?github\.com\//i, '')
    : 'No repository set';

  const handleExecute = () => {
    const state = useAgentStore.getState();
    if (!state.repoUrl || !state.teamName || !state.leaderName) {
      onOpenSettings?.();
      return;
    }
    runAgent();
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 px-5 py-3 bg-arbiter-surface border-b border-arbiter-border">
      {/* Repository display */}
      <div className="flex-1 min-w-0">
        <span className="text-[13px] text-arbiter-text-muted font-mono">
          Repository:{' '}
          <span className="text-arbiter-text font-semibold">{displayRepo}</span>
        </span>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 shrink-0">
        {!runComplete ? (
          <button
            onClick={handleExecute}
            disabled={isRunning}
            className="flex items-center gap-2 bg-arbiter-red hover:bg-arbiter-red-bright text-white text-[13px] font-mono font-bold px-5 py-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed tracking-wide"
          >
            {isRunning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {isRunning ? 'Running…' : 'Execute Agent'}
          </button>
        ) : (
          <button
            onClick={reset}
            className="flex items-center gap-2 bg-arbiter-red hover:bg-arbiter-red-bright text-white text-[13px] font-mono font-bold px-5 py-2 transition-all tracking-wide"
          >
            <RotateCcw className="w-4 h-4" />
            New Run
          </button>
        )}

        {runData?.branchName ? (
          <a
            href={`${repoUrl}/tree/${runData.branchName}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 border border-arbiter-border text-arbiter-text hover:bg-arbiter-surface hover:text-arbiter-green text-[13px] font-mono font-medium px-4 py-2 transition"
          >
            <GitBranch className="w-4 h-4" />
            {runData.branchName}
          </a>
        ) : (
          <button disabled className="flex items-center gap-2 border border-arbiter-border text-arbiter-text-dim/50 cursor-not-allowed text-[13px] font-mono font-medium px-4 py-2 transition">
            <GitBranch className="w-4 h-4" />
            Branch
          </button>
        )}

        {runData?.prUrl && (
          <a
            href={runData.prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 bg-arbiter-surface border border-arbiter-border text-arbiter-text hover:text-arbiter-green hover:border-arbiter-green text-[13px] font-mono font-medium px-4 py-2 transition"
          >
            <GitBranch className="w-4 h-4" />
            View PR
          </a>
        )}

        <button
          onClick={handleExecute}
          className="flex items-center gap-2 border border-arbiter-border text-arbiter-text-muted hover:bg-arbiter-surface hover:text-arbiter-text text-[13px] font-mono font-medium px-4 py-2 transition"
        >
          <RotateCcw className="w-4 h-4" />
          Retry
        </button>

        <button
          onClick={onOpenSettings}
          className="w-9 h-9 flex items-center justify-center border border-arbiter-border text-arbiter-text-dim hover:bg-arbiter-surface hover:text-arbiter-text transition"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
