import { create } from 'zustand';

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

/* ─────────── Terminal log sequence (streamed) ────────── */
const AGENT_LOG_SEQUENCE = [
  { agent: 'COORDINATOR', message: 'Initializing multi-agent reasoning pipeline...', type: 'info' },
  { agent: 'ANALYZER', message: 'Scanning test failure in payment-service/checkout.test.ts', type: 'warning' },
  { agent: 'ANALYZER', message: 'Root cause identified: Async timeout in Stripe webhook validation', type: 'warning' },
  { agent: 'PLANNER', message: 'Generating fix strategy: Increase timeout + add retry logic', type: 'success' },
  { agent: 'EXECUTOR', message: 'Applying patch to src/webhooks/stripe.ts', type: 'info' },
  { agent: 'EXECUTOR', message: 'Modifying timeout from 3000ms → 8000ms', type: 'info' },
  { agent: 'EXECUTOR', message: 'Adding exponential backoff retry (max 3 attempts)', type: 'info' },
  { agent: 'VALIDATOR', message: 'Running validation suite...', type: 'pending' },
  { agent: 'VALIDATOR', message: '✓ All tests passing (15/15)', type: 'success' },
  { agent: 'COORDINATOR', message: 'Healing cycle complete. CI/CD unblocked.', type: 'success' },
];

/* ──────────────── Mock data generator ────────────────── */
function generateMockRun(repoUrl, teamName, leaderName) {
  const BUG_TYPES = ['LINTING', 'SYNTAX', 'LOGIC', 'TYPE_ERROR', 'IMPORT', 'INDENTATION'];
  const FILES = [
    'src/index.js',
    'src/utils/parser.ts',
    'src/components/Header.jsx',
    'lib/helpers.py',
    'tests/test_main.py',
    'src/services/api.ts',
    'src/hooks/useAuth.js',
    'config/settings.json',
  ];

  const totalFixes = Math.floor(Math.random() * 8) + 4;
  const totalFailures = Math.floor(Math.random() * 3);
  const totalCommits = totalFixes + totalFailures + Math.floor(Math.random() * 10);
  const totalTimeMs = (Math.random() * 8 + 1) * 60 * 1000;

  const fixes = Array.from({ length: totalFixes + totalFailures }, (_, i) => ({
    id: i + 1,
    file: FILES[Math.floor(Math.random() * FILES.length)],
    bugType: BUG_TYPES[Math.floor(Math.random() * BUG_TYPES.length)],
    lineNumber: Math.floor(Math.random() * 300) + 1,
    commitMessage: `fix: resolve ${BUG_TYPES[Math.floor(Math.random() * BUG_TYPES.length)].toLowerCase()} issue in ${FILES[Math.floor(Math.random() * FILES.length)]}`,
    status: i < totalFixes ? 'Fixed' : 'Failed',
  }));

  const iterationCount = Math.floor(Math.random() * 3) + 3;
  const passed = totalFailures === 0;
  const iterations = Array.from({ length: iterationCount }, (_, i) => {
    const isPassing = i === iterationCount - 1 ? passed : i > iterationCount - 3 ? Math.random() > 0.3 : Math.random() > 0.6;
    return {
      id: i + 1,
      passed: isPassing,
      timestamp: new Date(Date.now() - (iterationCount - i) * 60000).toISOString(),
      label: `${i + 1}/${iterationCount}`,
    };
  });

  const baseScore = 100;
  const speedBonus = totalTimeMs < 5 * 60 * 1000 ? 10 : 0;
  const efficiencyPenalty = totalCommits > 20 ? (totalCommits - 20) * 2 : 0;
  const finalScore = Math.max(0, baseScore + speedBonus - efficiencyPenalty);

  return {
    repoUrl,
    teamName,
    leaderName,
    branchName: generateBranchName(teamName, leaderName),
    totalFixes,
    totalFailures,
    totalCommits,
    totalTimeMs,
    fixes,
    iterations,
    score: { base: baseScore, speedBonus, efficiencyPenalty, final: finalScore },
    passed,
    startedAt: new Date(Date.now() - totalTimeMs).toISOString(),
    completedAt: new Date().toISOString(),
  };
}

/* ──────────────────── Zustand Store ──────────────────── */
const useAgentStore = create((set, get) => ({
  // ── Config ──
  repoUrl: '',
  teamName: '',
  leaderName: '',

  // ── Dashboard stats ──
  stats: {
    totalRuns: 4721,
    successRate: 94.2,
    avgHealTime: '2m 34s',
    activeAgents: '8/12',
  },

  // ── Performance metrics ──
  performance: {
    speed: 85,
    efficiency: 92,
    accuracy: 78,
    coverage: 70,
    reliability: 88,
  },

  // ── Terminal logs ──
  terminalLogs: [],
  isStreaming: false,

  // ── Run state ──
  isRunning: false,
  runComplete: false,
  runData: null,

  // ── Setters ──
  setRepoUrl: (url) => set({ repoUrl: url }),
  setTeamName: (name) => set({ teamName: name }),
  setLeaderName: (name) => set({ leaderName: name }),

  // ── Run agent ──
  runAgent: () => {
    set({ isRunning: true, isStreaming: true, runComplete: false, runData: null, terminalLogs: [] });

    const now = new Date();
    let idx = 0;

    const streamNext = () => {
      if (idx >= AGENT_LOG_SEQUENCE.length) {
        // Streaming done — generate results
        const state = get();
        const data = generateMockRun(state.repoUrl, state.teamName, state.leaderName);
        set({
          isRunning: false,
          isStreaming: false,
          runComplete: true,
          runData: data,
          performance: {
            speed: 70 + Math.floor(Math.random() * 25),
            efficiency: 75 + Math.floor(Math.random() * 20),
            accuracy: 65 + Math.floor(Math.random() * 30),
            coverage: 60 + Math.floor(Math.random() * 30),
            reliability: 70 + Math.floor(Math.random() * 25),
          },
          stats: {
            ...state.stats,
            totalRuns: state.stats.totalRuns + 1,
          },
        });
        return;
      }

      const entry = AGENT_LOG_SEQUENCE[idx];
      const ts = new Date(now.getTime() + idx * 1000);
      const timeStr = ts.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      set((s) => ({
        terminalLogs: [...s.terminalLogs, { ...entry, time: timeStr }],
      }));

      idx++;
      setTimeout(streamNext, 600 + Math.random() * 600);
    };

    // Start streaming after a brief delay
    setTimeout(streamNext, 400);
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
      runData: null,
      terminalLogs: [],
    }),
}));

export default useAgentStore;
