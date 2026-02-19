import { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import useAgentStore from '../store/useAgentStore';

export function useAgentRealtime(runId) {
    const [logs, setLogs] = useState([]);
    const [status, setStatus] = useState('PENDING');

    useEffect(() => {
        if (!runId) return;

        // Fetch initial logs
        const fetchLogs = async () => {
            const { data } = await supabase
                .from('node_logs')
                .select('*')
                .eq('run_id', runId)
                .order('created_at', { ascending: true });

            if (data) setLogs(data);

            const { data: runData } = await supabase
                .from('agent_runs')
                .select('status')
                .eq('id', runId)
                .single();

            if (runData) setStatus(runData.status);
        };

        fetchLogs();

        // Subscription for logs
        const logsChannel = supabase
            .channel(`logs:${runId}`)
            .on(
                'postgres_changes',
                { event: 'INSERT', schema: 'public', table: 'node_logs', filter: `run_id=eq.${runId}` },
                (payload) => {
                    setLogs((prev) => [...prev, payload.new]);
                }
            )
            .subscribe();

        // Subscription for status updates
        const runChannel = supabase
            .channel(`run:${runId}`)
            .on(
                'postgres_changes',
                { event: 'UPDATE', schema: 'public', table: 'agent_runs', filter: `id=eq.${runId}` },
                (payload) => {
                    setStatus(payload.new.status);
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(logsChannel);
            supabase.removeChannel(runChannel);
        };
    }, [runId]);

    return { logs, status };
}
