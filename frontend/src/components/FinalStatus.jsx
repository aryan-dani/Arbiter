import { ShieldCheck, ShieldAlert, GitBranch, Clock, Hash, ExternalLink } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function FinalStatus() {
  const { runData } = useAgentStore();
  if (!runData) return null;

  const { passed, branchName, totalTimeMs, totalCommits, completedAt } = runData;

  return (
    <div
      className={`animate-slide-in p-6 md:p-8 shadow-lg border-2 transition-all ${passed
        ? 'bg-arbiter-green/10 border-arbiter-green/40'
        : 'bg-arbiter-red/10 border-arbiter-red-bright/40'
        }`}
    >
      <div className="flex flex-col sm:flex-row items-center gap-6">
        {/* Badge */}
        <div
          className={`w-20 h-20 flex items-center justify-center shrink-0 ${passed
            ? 'bg-arbiter-green/20'
            : 'bg-arbiter-red/20'
            }`}
          style={
            passed
              ? { animation: 'pulse-glow 2s ease-in-out infinite', boxShadow: '0 0 20px rgba(46,160,67,0.4)' }
              : { boxShadow: '0 0 20px rgba(196,58,21,0.3)' }
          }
        >
          {passed ? (
            <ShieldCheck className="w-10 h-10 text-arbiter-green" />
          ) : (
            <ShieldAlert className="w-10 h-10 text-arbiter-red-bright" />
          )}
        </div>

        {/* Text */}
        <div className="text-center sm:text-left flex-1">
          <h2
            className={`text-3xl md:text-4xl font-black tracking-wide font-mono ${passed ? 'text-arbiter-green' : 'text-arbiter-red-bright'
              }`}
          >
            {passed ? 'PASSED' : 'FAILED'}
          </h2>
          <p className="text-sm text-arbiter-text-dim mt-1 font-mono">
            CI/CD Pipeline {passed ? 'completed successfully' : 'did not pass all checks'}
          </p>
        </div>

        {/* Meta */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center sm:text-left">
          <div className="bg-arbiter-surface px-4 py-2 border border-arbiter-border">
            <div className="flex items-center gap-1.5 justify-center sm:justify-start">
              <Clock className="w-3 h-3 text-arbiter-text-dim" />
              <span className="text-[10px] text-arbiter-text-dim uppercase tracking-wider font-mono">Time</span>
            </div>
            <p className="text-sm font-semibold text-arbiter-text mt-0.5 font-mono">{(totalTimeMs / 60000).toFixed(1)} min</p>
          </div>
          <div className="bg-arbiter-surface px-4 py-2 border border-arbiter-border">
            <div className="flex items-center gap-1.5 justify-center sm:justify-start">
              <Hash className="w-3 h-3 text-arbiter-text-dim" />
              <span className="text-[10px] text-arbiter-text-dim uppercase tracking-wider font-mono">Commits</span>
            </div>
            <p className="text-sm font-semibold text-arbiter-text mt-0.5 font-mono">{totalCommits}</p>
          </div>
          <div className="bg-arbiter-surface px-4 py-2 border border-arbiter-border">
            <div className="flex items-center gap-1.5 justify-center sm:justify-start">
              <GitBranch className="w-3 h-3 text-arbiter-text-dim" />
              <span className="text-[10px] text-arbiter-text-dim uppercase tracking-wider font-mono">Branch</span>
            </div>
            <p className="text-xs font-mono font-semibold text-arbiter-red-bright mt-0.5 break-all">{branchName}</p>
          </div>
        </div>
      </div>

      {/* Completed timestamp & Actions */}
      <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-[11px] text-arbiter-text-dim font-mono order-2 sm:order-1">
          Completed at {new Date(completedAt).toLocaleString()}
        </p>

        <div className="flex items-center gap-3 order-1 sm:order-2">
          {runData.prUrl && (
            <a
              href={runData.prUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 bg-arbiter-text text-arbiter-bg px-5 py-2 text-[12px] font-mono font-bold hover:bg-arbiter-text/90 transition shadow-lg"
            >
              <ExternalLink className="w-4 h-4" />
              VIEW PULL REQUEST
            </a>
          )}
          {runData.repoUrl && branchName && !runData.prUrl && (
            <a
              href={`${runData.repoUrl.replace('.git', '')}/tree/${branchName}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 bg-arbiter-surface border border-arbiter-border text-arbiter-text px-5 py-2 text-[12px] font-mono font-bold hover:border-arbiter-red/40 transition shadow-sm"
            >
              <GitBranch className="w-4 h-4" />
              VIEW BRANCH
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
