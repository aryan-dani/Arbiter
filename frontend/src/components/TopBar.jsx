import { useState, useEffect } from 'react';
import { Shield, RefreshCw, Clock, Wrench, Terminal } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import useAgentStore from '../store/useAgentStore';

export default function TopBar() {
  const { isRunning, runData, runComplete, stats } = useAgentStore();

  /* ── Live CP Timer ── */
  const [elapsedTime, setElapsedTime] = useState('00:00');

  useEffect(() => {
    let interval;
    if (isRunning && runData?.startedAt) {
      const start = new Date(runData.startedAt).getTime();
      interval = setInterval(() => {
        const now = new Date().getTime();
        const diff = Math.floor((now - start) / 1000);
        const mins = Math.floor(diff / 60).toString().padStart(2, '0');
        const secs = (diff % 60).toString().padStart(2, '0');
        setElapsedTime(`${mins}:${secs}`);
      }, 1000);
    } else {
      setElapsedTime('00:00');
    }
    return () => clearInterval(interval);
  }, [isRunning, runData?.startedAt]);

  const metrics = [
    {
      icon: RefreshCw,
      label: 'ITERATIONS',
      value: runData?.iterations?.length ?? '—',
    },
    {
      icon: Clock,
      label: 'HEAL TIME',
      value: isRunning ? elapsedTime : (runComplete ? stats.avgHealTime : '—'),
    },
    {
      icon: Wrench,
      label: 'FIXES',
      value: runData?.totalFixes ?? '—',
    },
  ];

  return (
    <header className="flex items-center justify-between px-5 py-3 bg-arbiter-surface border-b border-arbiter-border">
      {/* Left: title */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-arbiter-red-bright" />
          <h1 className="text-[17px] font-extrabold text-arbiter-text tracking-tight font-mono">The Arbiter</h1>
        </div>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          <NavLink to="/" className={({ isActive }) => `px-3 py-1.5 text-[13px] font-mono font-bold tracking-wide transition-colors ${isActive ? 'text-arbiter-text bg-arbiter-surface border border-arbiter-border rounded' : 'text-arbiter-text-muted hover:text-arbiter-text'}`}>
            Home
          </NavLink>
          <NavLink to="/run" className={({ isActive }) => `px-3 py-1.5 text-[13px] font-mono font-bold tracking-wide transition-colors ${isActive ? 'text-arbiter-text bg-arbiter-surface border border-arbiter-border rounded' : 'text-arbiter-text-muted hover:text-arbiter-text'}`}>
            Run
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => `px-3 py-1.5 text-[13px] font-mono font-bold tracking-wide transition-colors ${isActive ? 'text-arbiter-text bg-arbiter-surface border border-arbiter-border rounded' : 'text-arbiter-text-muted hover:text-arbiter-text'}`}>
            History
          </NavLink>
        </nav>
      </div>

      {/* Right: real run metrics */}
      <div className="flex items-center gap-4 lg:gap-5">
        <div className="hidden sm:flex items-center gap-4 text-[11px] text-arbiter-text-muted font-mono">
          {metrics.map((m) => (
            <span key={m.label} className="flex items-center gap-1.5">
              <m.icon className="w-3.5 h-3.5 text-arbiter-text-dim" />
              <span className="uppercase tracking-wider font-medium text-arbiter-text-dim">{m.label}</span>
              <span className="text-arbiter-text font-semibold">{m.value}</span>
            </span>
          ))}
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

