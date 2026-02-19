import { Shield, Cpu, HardDrive, Timer, Terminal } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function TopBar() {
  const { isRunning } = useAgentStore();

  return (
    <header className="flex items-center justify-between px-5 py-3 bg-arbiter-surface border-b border-arbiter-border">
      {/* Left: title */}
      <div className="flex items-center gap-3">
        <Shield className="w-5 h-5 text-arbiter-red-bright" />
        <h1 className="text-[17px] font-extrabold text-arbiter-text tracking-tight font-mono">The Arbiter</h1>
        <span className="hidden sm:inline text-[10px] text-arbiter-text-dim font-mono border border-arbiter-border px-1.5 py-0.5 tracking-widest">v2.1.0</span>
        <span className="hidden lg:flex items-center gap-1.5 text-[12px] text-arbiter-text-dim ml-1">
          <Terminal className="w-3.5 h-3.5" />
          Autonomous CI/CD Healing Agent
        </span>
      </div>

      {/* Right: system metrics */}
      <div className="flex items-center gap-4 lg:gap-5">
        <div className="hidden sm:flex items-center gap-4 text-[11px] text-arbiter-text-muted font-mono">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-arbiter-text-dim" />
            <span className="uppercase tracking-wider font-medium text-arbiter-text-dim">CPU</span>
            <span className="text-arbiter-text font-semibold">23%</span>
          </span>
          <span className="flex items-center gap-1.5">
            <HardDrive className="w-3.5 h-3.5 text-arbiter-text-dim" />
            <span className="uppercase tracking-wider font-medium text-arbiter-text-dim">Memory</span>
            <span className="text-arbiter-text font-semibold">1.2GB</span>
          </span>
          <span className="flex items-center gap-1.5">
            <Timer className="w-3.5 h-3.5 text-arbiter-text-dim" />
            <span className="uppercase tracking-wider font-medium text-arbiter-text-dim">Latency</span>
            <span className="text-arbiter-text font-semibold">12ms</span>
          </span>
        </div>

        {/* Status badge */}
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-arbiter-amber animate-pulse' : 'bg-arbiter-green'}`} />
          <span className={`text-[11px] font-bold tracking-wider uppercase font-mono ${isRunning ? 'text-arbiter-amber' : 'text-arbiter-green'}`}>
            {isRunning ? 'RUNNING' : 'OPERATIONAL'}
          </span>
        </div>
      </div>
    </header>
  );
}
