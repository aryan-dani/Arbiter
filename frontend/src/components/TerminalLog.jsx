import { useEffect, useRef } from 'react';
import useAgentStore from '../store/useAgentStore';

const AGENT_COLORS = {
  COORDINATOR: 'text-cyan-400',
  ANALYZER: 'text-yellow-400',
  PLANNER: 'text-green-400',
  EXECUTOR: 'text-slate-300',
  VALIDATOR: 'text-purple-400',
};

const AGENT_BG = {
  COORDINATOR: 'bg-cyan-500/15 text-cyan-400',
  ANALYZER: 'bg-yellow-500/15 text-yellow-400',
  PLANNER: 'bg-green-500/15 text-green-400',
  EXECUTOR: 'bg-slate-500/15 text-slate-300',
  VALIDATOR: 'bg-purple-500/15 text-purple-400',
};

const MSG_COLORS = {
  info: 'text-slate-300',
  warning: 'text-yellow-300',
  success: 'text-green-400',
  pending: 'text-purple-300',
  error: 'text-red-400',
};

export default function TerminalLog() {
  const { terminalLogs, isStreaming } = useAgentStore();
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [terminalLogs]);

  return (
    <div className="bg-arbiter-bg border border-arbiter-border overflow-hidden flex flex-col h-[500px]">
      {/* Terminal header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-arbiter-surface border-b border-arbiter-border">
        <div className="flex items-center gap-3">
          {/* macOS dots */}
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-[12px] font-mono text-arbiter-text-dim">
            arbiter@rift-2026:~$
          </span>
        </div>

        {/* Streaming badge */}
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-arbiter-green animate-pulse' : 'bg-arbiter-text-dim'}`} />
          <span className={`text-[11px] font-semibold tracking-wider font-mono ${isStreaming ? 'text-arbiter-green' : 'text-arbiter-text-dim'}`}>
            {isStreaming ? 'STREAMING' : 'IDLE'}
          </span>
        </div>
      </div>

      {/* Log body */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-1 font-mono text-[13px] leading-relaxed">
        {terminalLogs.length === 0 && (
          <div className="text-arbiter-text-dim text-sm flex items-center gap-2 py-8 justify-center font-mono">
            <span className="animate-pulse">▌</span> Awaiting agent execution…
          </div>
        )}

        {terminalLogs.map((log, i) => (
          <div key={i} className="flex gap-3 animate-fade-in">
            {/* Timestamp */}
            <span className="text-arbiter-text-dim shrink-0 tabular-nums">{log.time}</span>

            {/* Agent badge */}
            <span className={`shrink-0 px-2 py-0 text-[11px] font-bold ${AGENT_BG[log.agent] || 'bg-arbiter-border text-arbiter-text-muted'}`}>
              [{log.agent}]
            </span>

            {/* Message */}
            <span className={`${MSG_COLORS[log.type] || 'text-slate-300'} wrap-break-word`}>
              {log.message}
            </span>
          </div>
        ))}

        {/* Blinking cursor */}
        {isStreaming && (
          <div className="text-arbiter-red-bright cursor-blink mt-1 font-bold">▌</div>
        )}
      </div>
    </div>
  );
}
