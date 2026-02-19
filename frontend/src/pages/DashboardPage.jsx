import { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import {
    GitBranch, Clock, CheckCircle, XCircle, AlertTriangle,
    ExternalLink, Calendar, Search, Filter
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function DashboardPage() {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('ALL'); // ALL, SUCCESS, FAILED

    useEffect(() => {
        fetchRuns();

        // Subscribe to new runs
        const channel = supabase
            .channel('dashboard_runs')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'agent_runs' }, () => {
                fetchRuns();
            })
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, []);

    const fetchRuns = async () => {
        setLoading(true);
        const { data, error } = await supabase
            .from('agent_runs')
            .select('*')
            .order('created_at', { ascending: false });

        if (!error) {
            setRuns(data);
        }
        setLoading(false);
    };

    const filteredRuns = runs.filter(r => {
        if (filter === 'ALL') return true;
        return r.status === filter;
    });

    const getStatusColor = (status) => {
        if (status === 'PASSED' || status === 'SUCCESS') return 'text-arbiter-green bg-arbiter-green/10 border-arbiter-green/20';
        if (status === 'FAILED') return 'text-arbiter-red-bright bg-arbiter-red/10 border-arbiter-red/20';
        if (status === 'ERROR') return 'text-arbiter-amber bg-arbiter-amber/10 border-arbiter-amber/20';
        return 'text-arbiter-text-muted bg-arbiter-surface border-arbiter-border';
    };

    const getStatusIcon = (status) => {
        if (status === 'PASSED' || status === 'SUCCESS') return CheckCircle;
        if (status === 'FAILED') return XCircle;
        if (status === 'ERROR') return AlertTriangle;
        return Clock;
    };

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
                <div>
                    <h1 className="text-2xl font-bold font-mono text-arbiter-text tracking-tight">Run History</h1>
                    <p className="text-arbiter-text-muted text-[13px] mt-1">
                        Global log of all autonomous healing execution cycles.
                    </p>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-2 bg-arbiter-surface border border-arbiter-border p-1 rounded-md">
                    {['ALL', 'SUCCESS', 'FAILED'].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-3 py-1.5 text-[11px] font-mono font-bold transition-all rounded ${filter === f
                                    ? 'bg-arbiter-text text-arbiter-bg'
                                    : 'text-arbiter-text-dim hover:text-arbiter-text'
                                }`}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="flex justify-center py-20">
                    <div className="w-6 h-6 border-2 border-arbiter-red border-t-transparent rounded-full animate-spin"></div>
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredRuns.map((run, i) => {
                        const StatusIcon = getStatusIcon(run.status);
                        const statusClass = getStatusColor(run.status);

                        return (
                            <motion.div
                                key={run.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className="group flex flex-col md:flex-row items-center gap-4 bg-arbiter-surface border border-arbiter-border p-4 hover:border-arbiter-border-subtle transition-all"
                            >
                                {/* Status Icon */}
                                <div className={`w-10 h-10 flex items-center justify-center rounded-full border ${statusClass}`}>
                                    <StatusIcon className="w-5 h-5" />
                                </div>

                                {/* Info */}
                                <div className="flex-1 min-w-0 grid grid-cols-1 md:grid-cols-4 gap-4 w-full">

                                    {/* Repo / Team */}
                                    <div className="col-span-1">
                                        <div className="text-[14px] font-bold text-arbiter-text truncate">
                                            {run.team_name || 'Unknown Team'}
                                        </div>
                                        <div className="text-[11px] text-arbiter-text-dim truncate font-mono mt-0.5">
                                            {run.target_repo?.replace('https://github.com/', '')}
                                        </div>
                                    </div>

                                    {/* Branch */}
                                    <div className="flex items-center gap-2 text-arbiter-text-muted">
                                        <GitBranch className="w-3.5 h-3.5" />
                                        <span className="text-[12px] font-mono truncate">{run.branch_name || '—'}</span>
                                    </div>

                                    {/* Stats */}
                                    <div className="flex items-center gap-6">
                                        <div>
                                            <div className="text-[9px] text-arbiter-text-dim uppercase tracking-wider">SCORE</div>
                                            <div className={`font-mono font-bold ${run.final_score >= 90 ? 'text-arbiter-green' : 'text-arbiter-text'}`}>
                                                {run.final_score ?? '—'}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-[9px] text-arbiter-text-dim uppercase tracking-wider">DURATION</div>
                                            <div className="font-mono text-[12px] text-arbiter-text-muted">
                                                {run.duration ? `${Math.round(run.duration)}s` : '—'}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center justify-end gap-3">
                                        {run.pr_url && (
                                            <a
                                                href={run.pr_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1.5 text-[11px] font-bold text-arbiter-text bg-arbiter-bg border border-arbiter-border px-3 py-1.5 hover:border-arbiter-green hover:text-arbiter-green transition"
                                            >
                                                <ExternalLink className="w-3 h-3" />
                                                PR
                                            </a>
                                        )}
                                        <div className="text-[10px] text-arbiter-text-dim font-mono">
                                            {new Date(run.created_at).toLocaleDateString()}
                                        </div>
                                    </div>

                                </div>
                            </motion.div>
                        );
                    })}

                    {filteredRuns.length === 0 && (
                        <div className="text-center py-20 text-arbiter-text-dim italic">
                            No runs found for this filter.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
