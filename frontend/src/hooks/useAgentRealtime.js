import { useEffect, useState } from 'react';
import { API_BASE } from '../api';

/**
 * Polls backend for node logs while a run is active (replaces Supabase Realtime).
 */
export function useAgentRealtime(runId) {
    const [logs, setLogs] = useState([]);
    const [status, setStatus] = useState('PENDING');

    useEffect(() => {
        if (!runId) return;

        let cancelled = false;

        const fetchLogs = async () => {
            try {
                const [logsRes, runRes] = await Promise.all([
                    fetch(`${API_BASE}/api/runs/${encodeURIComponent(runId)}/logs`),
                    fetch(`${API_BASE}/api/runs/${encodeURIComponent(runId)}`),
                ]);
                if (cancelled) return;

                if (logsRes.ok) {
                    const body = await logsRes.json();
                    const list = Array.isArray(body?.logs) ? body.logs : [];
                    const normalized = list.map((row) => {
                        let content = row.content;
                        if (typeof content === 'string') {
                            try {
                                content = JSON.parse(content);
                            } catch {
                                content = {};
                            }
                        }
                        return { ...row, content: content ?? {} };
                    });
                    setLogs(normalized);
                }
                if (runRes.ok) {
                    const row = await runRes.json();
                    if (row?.status) setStatus(row.status);
                }
            } catch {
                /* keep previous state */
            }
        };

        fetchLogs();
        const interval = setInterval(fetchLogs, 1500);

        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [runId]);

    return { logs, status };
}
