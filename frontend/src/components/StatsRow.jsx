import { useState, useEffect } from 'react';
import { Zap, CheckCircle, Clock, Wrench } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';
import { supabase } from '../supabaseClient';

export default function StatsRow() {
  const { stats, runData, runComplete, isRunning } = useAgentStore();
  const [elapsedTime, setElapsedTime] = useState('00:00');
  const [dbStats, setDbStats] = useState({ totalRuns: 0, lastRunStatus: null });

  // ── Timer Logic ──
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

  // ── Fetch Global Stats ──
  useEffect(() => {
    async function fetchGlobalStats() {
      // Total Runs
      const { count } = await supabase
        .from('agent_runs')
        .select('*', { count: 'exact', head: true });

      // Last Run Status
      const { data } = await supabase
        .from('agent_runs')
        .select('status')
        .order('created_at', { ascending: false })
        .limit(1);

      setDbStats({
        totalRuns: count || 0,
        lastRunStatus: data?.[0]?.status || null
      });
    }
    fetchGlobalStats();
  }, [runComplete]); // Re-fetch when a run completes

  const STATS = [
    {
      label: 'TOTAL RUNS',
      key: 'totalRuns',
      icon: Zap,
      value: dbStats.totalRuns, // Use DB count
      color: 'text-arbiter-blue',
    },
    {
      label: 'LAST RUN',
      key: 'lastRun',
      icon: CheckCircle,
      value: (() => {
        if (isRunning) return 'PENDING...';
        if (runComplete) return runData?.passed ? 'PASSED' : 'FAILED';
        return dbStats.lastRunStatus || 'N/A';
      })(),
      color: (() => {
        if (isRunning) return 'text-arbiter-text-dim animate-pulse';
        const status = runComplete ? (runData?.passed ? 'PASSED' : 'FAILED') : dbStats.lastRunStatus;
        if (status === 'PASSED' || status === 'SUCCESS') return 'text-arbiter-green';
        if (status === 'FAILED') return 'text-arbiter-red-bright';
        return 'text-arbiter-text-dim';
      })(),
    },
    {
      label: 'HEAL TIME',
      key: 'healTime',
      icon: Clock,
      value: isRunning ? elapsedTime : (runComplete ? stats.avgHealTime : '—'),
      color: 'text-arbiter-amber',
    },
    {
      label: 'FIXES APPLIED',
      key: 'totalFixes',
      icon: Wrench,
      value: runData?.totalFixes ?? 0,
      color: 'text-arbiter-purple',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 px-5 py-4">
      {STATS.map((s) => (
        <div
          key={s.key}
          className="bg-arbiter-surface border border-arbiter-border px-4 py-4 flex flex-col gap-2"
        >
          {/* Header */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold tracking-[0.12em] uppercase text-arbiter-text-dim font-mono">
              {s.label}
            </span>
            <s.icon className="w-4 h-4 text-arbiter-text-dim" />
          </div>

          {/* Value */}
          <div className="flex items-end gap-2">
            <span className={`text-2xl lg:text-3xl font-black font-mono tracking-tight ${s.color}`}>
              {s.value}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
