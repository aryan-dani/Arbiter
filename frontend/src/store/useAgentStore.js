import { create } from 'zustand';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ─────────────────────── Utility ─────────────────────── */
export function generateBranchName(teamName, leaderName) {
  const sanitize = (str) =>
    str
      .toUpperCase()
      .replace(/[^A-Z0-9 ]/g, '')
      .trim()
      .replace(/\s+/g, '_');
  return `${sanitize(teamName)}_${sanitize(leaderName)}_AI_Fix`;
}

/* ─────── Terminal log messages for progress streaming ─── */
const PROGRESS_MESSAGES = [
  { agent: 'COORDINATOR', message: 'Initializing autonomous healing pipeline...', type: 'info' },
  { agent: 'DISCOVERY', message: 'Cloning repository and scanning project structure...', type: 'info' },
  { agent: 'DISCOVERY', message: 'Detecting stack and locating test files...', type: 'info' },
  { agent: 'TESTER', message: 'Launching Docker container for sandboxed test execution...', type: 'info' },
  { agent: 'TESTER', message: 'Running test suite...', type: 'warning' },
  { agent: 'DEBUGGER', message: 'Analyzing test failures with Gemini AI...', type: 'warning' },
  { agent: 'FIXER', message: 'Generating code fix via Gemini 2.0 Flash...', type: 'info' },
  { agent: 'GIT', message: 'Committing fix with [AI-AGENT] prefix...', type: 'info' },
  { agent: 'TESTER', message: 'Re-running test suite to verify fix...', type: 'pending' },
  { agent: 'SCORING', message: 'Calculating final score and performance metrics...', type: 'info' },
];

/* ──────────────────── Zustand Store ──────────────────── */
const useAgentStore = create((set, get) => ({
  // ── Config ──
  repoUrl: '',
  teamName: '',
  leaderName: '',
  aiModel: 'gemini-2.0-flash',
  maxRetries: 5,

  // ── Dashboard stats ──
  stats: {
    totalRuns: 0,
    successRate: 0,
    avgHealTime: 'N/A',
    activeAgents: '6/6',
  },

  // ── Performance metrics ──
  performance: {
    speed: 0,
    efficiency: 0,
    accuracy: 0,
    coverage: 0,
    reliability: 0,
  },

  // ── Terminal logs ──
  terminalLogs: [],
  isStreaming: false,

  // ── Run state ──
  isRunning: false,
  activeAgent: null,
  runComplete: false,
  runData: null,
  runId: null,
  error: null,

  // ── Setters ──
  setRepoUrl: (url) => set({ repoUrl: url }),
  setTeamName: (name) => set({ teamName: name }),
  setLeaderName: (name) => set({ leaderName: name }),
  setAiModel: (model) => set({ aiModel: model }),
  setMaxRetries: (count) => set({ maxRetries: count }),

  // ── Append a terminal log entry ──
  _addLog: (agent, message, type = 'info') => {
    const time = new Date().toLocaleTimeString('en-GB', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
    set((s) => ({
      terminalLogs: [...s.terminalLogs, { agent, message, type, time }],
      activeAgent: agent, // Track active agent for visualization
    }));
  },

  // ── Real-time Updates ──
  setStatus: (status) => set((s) => ({
    runData: { ...s.runData, final_status: status },
    runComplete: status === 'PASSED' || status === 'FAILED' || status === 'ERROR'
  })),

  updateFromLog: (log) => {
    const { _addLog, performance, runData } = get();

    // Parse Supabase log entry
    const agentMap = {
      'discovery_node': 'DISCOVERY',
      'tester_node': 'TESTER',
      'debugger_node': 'DEBUGGER',
      'fixer_node': 'FIXER',
      'git_node': 'GIT',
      'scoring_node': 'SCORING'
    };
    const agent = agentMap[log.node_name] || 'COORDINATOR';

    // Add to terminal
    _addLog(agent, log.log_type === 'INFO' ? log.content : (typeof log.content === 'string' ? log.content : JSON.stringify(log.content)), log.log_type.toLowerCase());

    // Update Metrics Dynamic Logic
    if (log.log_type === 'FIX_APPLIED') {
      const fixEntry = {
        id: (runData?.fixes?.length || 0) + 1,
        file: log.content.path || 'unknown',
        bugType: log.content.bug_type || 'LOGIC',
        lineNumber: log.content.line || 0,
        commitMessage: log.content.commit_message || 'AI Fix',
        status: 'Fixed'
      };

      set((s) => ({
        performance: {
          ...s.performance,
          coverage: Math.min(100, s.performance.coverage + 10),
          efficiency: Math.min(100, s.performance.efficiency + 5)
        },
        runData: {
          ...(s.runData || {}),
          fixes: [...(s.runData?.fixes || []), fixEntry],
          totalFixes: (s.runData?.fixes?.length || 0) + 1
        }
      }));
    }

    if (agent === 'TESTER') {
      const contentStr = typeof log.content === 'string' ? log.content : JSON.stringify(log.content);

      // Update reliability
      if (contentStr.includes('FAIL')) {
        set((s) => ({
          performance: { ...s.performance, reliability: Math.max(0, s.performance.reliability - 10) }
        }));
      }

      // Infer Iteration Logic: "Testing Complete" usually marks end of an iteration
      if (contentStr.includes('Testing Complete')) {
        const currentIter = (runData?.iterations?.length || 0) + 1;
        const passed = contentStr.includes('Exit Code: 0');

        const newIter = {
          id: currentIter,
          passed: passed,
          timestamp: new Date().toISOString(),
          label: `${currentIter}`,
        };

        set((s) => ({
          runData: {
            ...(s.runData || {}),
            iterations: [...(s.runData?.iterations || []), newIter]
          }
        }));
      }
    }
  },

  // ── Run agent (real backend) ──
  runAgent: async () => {
    const { repoUrl, teamName, leaderName, _addLog } = get();
    set({
      isRunning: true,
      isStreaming: true,
      runComplete: false,
      runData: {
        repoUrl, teamName, leaderName,
        fixes: [],
        iterations: [],
        score: null,
        totalFixes: 0
      },
      terminalLogs: [],
      error: null
    });

    _addLog('COORDINATOR', 'Sending request to backend agent...', 'info');

    try {
      // POST /start-healing
      const res = await fetch(`${API_BASE}/start-healing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          team_name: teamName,
          leader_name: leaderName,
          max_iterations: get().maxRetries,
          model_name: get().aiModel
        }),
      });

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();

      // Store runId for real-time subscription
      if (data.run_id) {
        set({ runId: data.run_id });
      }

      _addLog('COORDINATOR', 'Healing agent launched in background...', 'success');

      // Stream progress messages while polling
      let msgIdx = 0;
      const streamInterval = setInterval(() => {
        if (msgIdx < PROGRESS_MESSAGES.length) {
          const { _addLog: al } = get();
          al(PROGRESS_MESSAGES[msgIdx].agent, PROGRESS_MESSAGES[msgIdx].message, PROGRESS_MESSAGES[msgIdx].type);
          msgIdx++;
        }
      }, 3000);

      // Poll /status/{teamName} every 5 seconds
      const poll = async () => {
        try {
          const statusRes = await fetch(`${API_BASE}/status/${encodeURIComponent(teamName)}`);
          const data = await statusRes.json();

          if (data.status === 'done' && data.result) {
            clearInterval(streamInterval);
            const result = data.result;
            const fixes = result.fixes_applied || [];
            const commitCount = fixes.length;
            const duration = result.total_time || 0;

            const _addLogFn = get()._addLog;
            if (result.final_status === 'PASSED') {
              _addLogFn('COORDINATOR', `✓ All tests passing. Healing complete!`, 'success');
            } else {
              _addLogFn('COORDINATOR', `✗ Max retries reached. Final status: ${result.final_status}`, 'warning');
            }

            // Map fixes to frontend format
            const mappedFixes = fixes.map((f, i) => ({
              id: i + 1,
              file: f.path || f.file || 'unknown',
              bugType: f.bug_type || 'LOGIC',
              lineNumber: f.line || 0,
              commitMessage: f.commit_message || '[AI-AGENT] Fix applied',
              status: 'Fixed',
            }));

            // Build timeline from retry_count
            const iterations = [];
            const maxIterations = (result.retry_count || 0) + 1;
            for (let i = 0; i < maxIterations; i++) {
              const isPassed = i === maxIterations - 1 && result.final_status === 'PASSED';
              iterations.push({
                id: i + 1,
                passed: isPassed,
                timestamp: result.started_at || new Date().toISOString(),
                label: `${i + 1}/${Math.max(maxIterations, 5)}`,
              });
            }

            const baseScore = result.base_score || 100;
            const speedBonus = result.speed_bonus || 0;
            const penalty = result.efficiency_penalty || 0;

            set({
              isRunning: false,
              isStreaming: false,
              runComplete: true,
              runData: {
                repoUrl: result.repo_url,
                teamName: result.team_name,
                leaderName: result.leader_name,
                branchName: result.branch_name || generateBranchName(result.team_name, result.leader_name),
                totalFixes: commitCount,
                totalFailures: result.final_status === 'PASSED' ? 0 : 1,
                totalCommits: commitCount,
                totalTimeMs: duration * 1000,
                fixes: mappedFixes,
                iterations,
                score: {
                  base: baseScore,
                  speedBonus,
                  efficiencyPenalty: penalty,
                  final: result.final_score || baseScore + speedBonus - penalty,
                },
                passed: result.final_status === 'PASSED',
                startedAt: result.started_at || new Date().toISOString(),
                completedAt: result.completed_at || new Date().toISOString(),
              },
              performance: {
                speed: speedBonus > 0 ? 95 : Math.max(50, 85 - Math.floor(duration / 60) * 3),
                efficiency: Math.max(40, 100 - penalty * 2),
                accuracy: result.final_status === 'PASSED' ? 90 : 60,
                coverage: Math.min(95, 60 + commitCount * 5),
                reliability: result.final_status === 'PASSED' ? 88 : 55,
              },
              stats: {
                totalRuns: get().stats.totalRuns + 1,
                successRate: result.final_status === 'PASSED' ? 100 : 0,
                avgHealTime: `${Math.floor(duration / 60)}m ${Math.floor(duration % 60)}s`,
                activeAgents: '6/6',
              },
            });

          } else if (data.status === 'error') {
            clearInterval(streamInterval);
            const _addLogFn = get()._addLog;
            _addLogFn('COORDINATOR', `Agent error: ${data.error}`, 'warning');
            set({ isRunning: false, isStreaming: false, error: data.error });

          } else {
            // Still running — poll again
            setTimeout(poll, 5000);
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
          setTimeout(poll, 5000);
        }
      };

      // Start polling after 5 seconds
      setTimeout(poll, 5000);

    } catch (err) {
      const _addLogFn = get()._addLog;
      _addLogFn('COORDINATOR', `Failed to start agent: ${err.message}`, 'warning');
      set({ isRunning: false, isStreaming: false, error: err.message });
    }
  },

  // ── Reset ──
  reset: () =>
    set({
      repoUrl: '',
      teamName: '',
      leaderName: '',
      isRunning: false,
      isStreaming: false,
      runComplete: false,
      runComplete: false,
      runData: null,
      runId: null,
      terminalLogs: [],
      error: null,
    }),
}));

export default useAgentStore;
