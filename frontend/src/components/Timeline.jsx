import { Clock, CheckCircle2, XCircle } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function Timeline() {
  const { runData } = useAgentStore();
  if (!runData) return null;

  const { iterations } = runData;

  return (
    <div className="animate-slide-in bg-arbiter-surface border border-arbiter-border p-6 shadow-lg">
      <h2 className="text-lg font-bold text-arbiter-text mb-5 flex items-center gap-2 font-mono">
        <Clock className="w-5 h-5 text-arbiter-red-bright" />
        CI/CD Pipeline Timeline
      </h2>

      {/* Horizontal timeline (desktop) */}
      <div className="hidden md:block overflow-x-auto pb-2">
        <div className="flex items-start gap-0 min-w-max">
          {iterations.map((iter, idx) => (
            <div key={iter.id} className="flex items-start">
              {/* Node */}
              <div className="flex flex-col items-center w-36">
                <div
                  className={`w-10 h-10 flex items-center justify-center border-2 transition-all ${
                    iter.passed
                      ? 'border-arbiter-green bg-arbiter-green/20'
                      : 'border-arbiter-red-bright bg-arbiter-red/20'
                  }`}
                >
                  {iter.passed ? (
                    <CheckCircle2 className="w-5 h-5 text-arbiter-green" />
                  ) : (
                    <XCircle className="w-5 h-5 text-arbiter-red-bright" />
                  )}
                </div>

                <div className="mt-2 text-center">
                  <span className={`text-xs font-bold font-mono ${iter.passed ? 'text-arbiter-green' : 'text-arbiter-red-bright'}`}>
                    {iter.passed ? 'PASS' : 'FAIL'}
                  </span>
                  <p className="text-xs text-arbiter-text-dim mt-0.5 font-mono">Iteration {iter.label}</p>
                  <p className="text-[10px] text-arbiter-text-dim mt-0.5 font-mono">
                    {new Date(iter.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </p>
                </div>
              </div>

              {/* Connector line */}
              {idx < iterations.length - 1 && (
                <div className="flex items-center h-10">
                  <div className={`w-16 h-0.5 ${iter.passed ? 'bg-arbiter-green/50' : 'bg-arbiter-red-bright/50'}`} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Vertical timeline (mobile) */}
      <div className="md:hidden space-y-0">
        {iterations.map((iter, idx) => (
          <div key={iter.id} className="flex gap-4">
            {/* Vertical line + dot */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 flex items-center justify-center border-2 shrink-0 ${
                  iter.passed
                    ? 'border-arbiter-green bg-arbiter-green/20'
                    : 'border-arbiter-red-bright bg-arbiter-red/20'
                }`}
              >
                {iter.passed ? (
                  <CheckCircle2 className="w-4 h-4 text-arbiter-green" />
                ) : (
                  <XCircle className="w-4 h-4 text-arbiter-red-bright" />
                )}
              </div>
              {idx < iterations.length - 1 && (
                <div className={`w-0.5 flex-1 min-h-[2rem] ${iter.passed ? 'bg-arbiter-green/40' : 'bg-arbiter-red-bright/40'}`} />
              )}
            </div>

            {/* Content */}
            <div className="pb-6">
              <span className={`text-xs font-bold font-mono ${iter.passed ? 'text-arbiter-green' : 'text-arbiter-red-bright'}`}>
                {iter.passed ? 'PASS' : 'FAIL'} — Iteration {iter.label}
              </span>
              <p className="text-[11px] text-arbiter-text-dim mt-0.5 font-mono">
                {new Date(iter.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
