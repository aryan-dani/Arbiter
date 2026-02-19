import { Shield } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

const PIPELINE_STAGES = [
  { key: 'DISCOVERY', label: 'Discovery' },
  { key: 'TESTER', label: 'Tester' },
  { key: 'DEBUGGER', label: 'Debugger' },
  { key: 'FIXER', label: 'Fixer' },
  { key: 'GIT', label: 'Git' },
];

function getStageStatus(stageKey, terminalLogs, isRunning, runComplete, runData) {
  if (!terminalLogs.length && !runComplete) return 'idle';

  // Find the last log that belongs to a pipeline stage
  const lastLog = [...terminalLogs].reverse().find((l) =>
    PIPELINE_STAGES.some((s) => s.key === l.agent)
  );
  const activeKey = lastLog?.agent ?? null;
  const stageIdx = PIPELINE_STAGES.findIndex((s) => s.key === stageKey);
  const activeIdx = PIPELINE_STAGES.findIndex((s) => s.key === activeKey);

  if (runComplete) {
    // After run: all green if passed, last one red if failed
    if (runData?.passed) return 'done';
    // If failed, stages up to the active stage are done, active is error
    if (stageIdx < activeIdx) return 'done';
    if (stageIdx === activeIdx) return 'error';
    return 'idle';
  }

  if (isRunning) {
    if (stageIdx < activeIdx) return 'done';
    if (stageIdx === activeIdx) return 'running';
    return 'idle';
  }

  return 'idle';
}

export default function Sidebar() {
  const { terminalLogs, isRunning, runComplete, runData } = useAgentStore();

  return (
    <aside className="hidden md:flex flex-col items-center w-[52px] bg-arbiter-bg border-r border-arbiter-border py-4 gap-3 shrink-0">
      {/* Logo */}
      <div className="w-9 h-9 flex items-center justify-center border border-arbiter-red bg-arbiter-red/10 mb-1">
        <Shield className="w-5 h-5 text-white" />
      </div>

      {/* Pipeline stage tracker */}
      <div className="flex flex-col items-center gap-3 pt-2">
        {PIPELINE_STAGES.map((stage) => {
          const status = getStageStatus(
            stage.key, terminalLogs, isRunning, runComplete, runData
          );
          return (
            <div key={stage.key} className="relative group flex flex-col items-center gap-1">
              {/* Status dot */}
              <span
                className={[
                  'w-[10px] h-[10px] rounded-full transition-all duration-500',
                  status === 'idle' ? 'bg-arbiter-text-dim/30' : '',
                  status === 'running' ? 'bg-arbiter-amber animate-pulse' : '',
                  status === 'done' ? 'bg-arbiter-green' : '',
                  status === 'error' ? 'bg-arbiter-red-bright' : '',
                ].join(' ')}
              />
              {/* Tooltip */}
              <span className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2 py-0.5 bg-arbiter-surface border border-arbiter-border text-[10px] font-mono text-arbiter-text whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                {stage.label}
                <span className={[
                  'ml-1.5 font-bold',
                  status === 'idle' ? 'text-arbiter-text-dim' : '',
                  status === 'running' ? 'text-arbiter-amber' : '',
                  status === 'done' ? 'text-arbiter-green' : '',
                  status === 'error' ? 'text-arbiter-red-bright' : '',
                ].join(' ')}>
                  {status === 'idle' ? 'IDLE' : status === 'running' ? 'RUNNING' : status === 'done' ? 'DONE' : 'FAILED'}
                </span>
              </span>

              {/* Connector line (not after last) */}
              {stage.key !== 'GIT' && (
                <span className="w-px h-3 bg-arbiter-border" />
              )}
            </div>
          );
        })}
      </div>

      {/* Vertical label at bottom */}
      <div className="flex-1 flex items-end pb-2">
        <span
          className="text-[10px] font-bold tracking-[0.25em] text-arbiter-text-dim uppercase font-mono"
          style={{ writingMode: 'vertical-lr' }}
        >
          ARBITER
        </span>
      </div>
    </aside>
  );
}
