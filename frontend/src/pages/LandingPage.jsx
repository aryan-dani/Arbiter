import { useState, useEffect, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Shield, Terminal, GitBranch, Cpu, ArrowRight,
  CheckCircle, Zap, Users, Lock, Activity,
  Layers, BarChart3, Clock, Code2, Box, Database
} from 'lucide-react';

/* ─────────── ANIMATION VARIANTS ─────────── */
const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.2 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] } },
};

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.6 } },
};

/* ─────────── TERMINAL LOG DATA ─────────── */
const TERMINAL_LINES = [
  { time: '14:32:01', agent: 'COORDINATOR', text: 'Initializing multi-agent reasoning pipeline...', color: 'text-arbiter-text-muted' },
  { time: '14:32:02', agent: 'ANALYZER', text: 'Scanning test failure in checkout.test.ts', color: 'text-arbiter-amber' },
  { time: '14:32:03', agent: 'ANALYZER', text: 'Root cause: Async timeout in Stripe webhook', color: 'text-arbiter-amber' },
  { time: '14:32:04', agent: 'PLANNER', text: 'Strategy: Increase timeout + retry logic', color: 'text-arbiter-green' },
  { time: '14:32:05', agent: 'EXECUTOR', text: 'Applying patch to src/webhooks/stripe.ts', color: 'text-arbiter-text' },
  { time: '14:32:06', agent: 'AUDITOR', text: 'Validating fix against 15 test cases...', color: 'text-purple-400' },
  { time: '14:32:07', agent: 'AUDITOR', text: '✓ All tests passing (15/15)', color: 'text-arbiter-green' },
  { time: '14:32:08', agent: 'COORDINATOR', text: 'Healing cycle complete. Pipeline unblocked.', color: 'text-arbiter-green' },
];

/* ─────────── VISUAL TERMINAL ─────────── */
function VisualTerminal() {
  const [visibleLines, setVisibleLines] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const containerRef = useRef(null);

  useEffect(() => {
    if (currentIdx >= TERMINAL_LINES.length) {
      // restart after pause
      const t = setTimeout(() => {
        setVisibleLines([]);
        setCurrentIdx(0);
      }, 3000);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => {
      setVisibleLines((prev) => [...prev, TERMINAL_LINES[currentIdx]]);
      setCurrentIdx((i) => i + 1);
    }, 700 + Math.random() * 400);
    return () => clearTimeout(t);
  }, [currentIdx]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [visibleLines]);

  const agentColors = {
    COORDINATOR: 'bg-arbiter-red/20 text-arbiter-red-bright',
    ANALYZER: 'bg-amber-500/15 text-arbiter-amber',
    PLANNER: 'bg-green-500/15 text-arbiter-green',
    EXECUTOR: 'bg-arbiter-border/60 text-arbiter-text-muted',
    AUDITOR: 'bg-purple-500/15 text-purple-400',
  };

  return (
    <div className="border border-arbiter-border bg-arbiter-bg overflow-hidden">
      {/* Terminal chrome */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-arbiter-border bg-arbiter-surface">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-arbiter-red" />
          <div className="w-2.5 h-2.5 rounded-full bg-arbiter-amber" />
          <div className="w-2.5 h-2.5 rounded-full bg-arbiter-green" />
        </div>
        <span className="font-mono text-[11px] text-arbiter-text-dim tracking-wider">
          arbiter@rift-2026:~$
        </span>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-arbiter-green animate-pulse" />
          <span className="font-mono text-[10px] text-arbiter-green tracking-widest font-semibold">LIVE</span>
        </div>
      </div>

      {/* Terminal body */}
      <div ref={containerRef} className="h-[280px] md:h-[320px] overflow-y-auto px-4 py-3 font-mono text-[12px] md:text-[13px] leading-relaxed space-y-1.5">
        {visibleLines.map((line, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25 }}
            className="flex gap-3"
          >
            <span className="text-arbiter-text-dim tabular-nums shrink-0">{line.time}</span>
            <span className={`shrink-0 px-1.5 py-0 text-[10px] font-bold tracking-wide ${agentColors[line.agent] || ''}`}>
              [{line.agent}]
            </span>
            <span className={line.color}>{line.text}</span>
          </motion.div>
        ))}
        {currentIdx < TERMINAL_LINES.length && (
          <span className="text-arbiter-red-bright cursor-blink font-bold">▌</span>
        )}
      </div>
    </div>
  );
}

/* ─────────── STAT COUNTER ─────────── */
function StatNumber({ value, suffix = '', label }) {
  return (
    <div className="text-center">
      <div className="font-mono font-extrabold text-3xl md:text-4xl text-arbiter-text tracking-tight">
        {value}
        <span className="text-arbiter-red-bright">{suffix}</span>
      </div>
      <div className="text-[11px] text-arbiter-text-dim uppercase tracking-[0.15em] font-medium mt-1">{label}</div>
    </div>
  );
}

/* ─────────── BENTO TILE ─────────── */
function BentoTile({ icon: Icon, title, description, children, className = '', span = '' }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? 'visible' : 'hidden'}
      variants={fadeUp}
      className={`border border-arbiter-border bg-arbiter-surface p-6 relative overflow-hidden group ${span} ${className}`}
    >
      {/* Corner accent */}
      <div className="absolute top-0 left-0 w-8 h-px bg-arbiter-red" />
      <div className="absolute top-0 left-0 w-px h-8 bg-arbiter-red" />

      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 border border-arbiter-border flex items-center justify-center bg-arbiter-bg">
            <Icon className="w-4 h-4 text-arbiter-red-bright" />
          </div>
          <h3 className="font-mono font-bold text-[14px] text-arbiter-text tracking-tight uppercase">{title}</h3>
        </div>
        <p className="text-[13px] text-arbiter-text-muted leading-relaxed font-light">{description}</p>
        {children}
      </div>
    </motion.div>
  );
}

/* ─────────── AGENT FLOW VISUAL ─────────── */
function AgentFlowDiagram() {
  const agents = [
    { name: 'ARBITER', role: 'Coordinator', icon: Shield, active: true },
    { name: 'CODER', role: 'Fix Generator', icon: Code2, active: false },
    { name: 'AUDITOR', role: 'Validator', icon: Lock, active: false },
  ];

  return (
    <div className="mt-5 flex items-center justify-between gap-2">
      {agents.map((a, i) => (
        <div key={a.name} className="flex items-center gap-2">
          <div className={`border px-3 py-2 flex items-center gap-2 ${a.active ? 'border-arbiter-red bg-arbiter-red/10' : 'border-arbiter-border bg-arbiter-bg'}`}>
            <a.icon className={`w-3.5 h-3.5 ${a.active ? 'text-arbiter-red-bright' : 'text-arbiter-text-dim'}`} />
            <div>
              <div className={`font-mono text-[10px] font-bold tracking-widest ${a.active ? 'text-arbiter-red-bright' : 'text-arbiter-text-muted'}`}>{a.name}</div>
              <div className="text-[9px] text-arbiter-text-dim">{a.role}</div>
            </div>
          </div>
          {i < agents.length - 1 && (
            <ArrowRight className="w-3 h-3 text-arbiter-text-dim" />
          )}
        </div>
      ))}
    </div>
  );
}

/* ─────────── COMMIT LOG VISUAL ─────────── */
function CommitLog() {
  const commits = [
    { hash: 'a3f2c1d', msg: 'fix(api): resolve timeout in webhook handler', agent: '[AI-AGENT]', status: 'pass' },
    { hash: 'b8e4f2a', msg: 'fix(test): update async assertions', agent: '[AI-AGENT]', status: 'pass' },
    { hash: 'c1d9e3b', msg: 'chore: bump retry limit to 3', agent: '[AI-AGENT]', status: 'pending' },
  ];

  return (
    <div className="mt-5 space-y-2">
      {commits.map((c) => (
        <div key={c.hash} className="flex items-center gap-3 font-mono text-[11px] border border-arbiter-border-subtle px-3 py-1.5 bg-arbiter-bg">
          <span className="text-arbiter-red-bright font-bold">{c.hash.slice(0, 7)}</span>
          <span className="text-arbiter-text-muted flex-1 truncate">{c.msg}</span>
          <span className="text-arbiter-text-dim text-[9px]">{c.agent}</span>
          <span className={`w-1.5 h-1.5 rounded-full ${c.status === 'pass' ? 'bg-arbiter-green' : 'bg-arbiter-amber'}`} />
        </div>
      ))}
    </div>
  );
}

/* ─────────── SCORING VISUAL ─────────── */
function ScoringVisual() {
  const bars = [
    { label: 'BASE', value: 100, max: 110, color: 'bg-arbiter-text-muted' },
    { label: 'SPEED', value: 10, max: 110, color: 'bg-arbiter-green' },
    { label: 'PENALTY', value: -4, max: 110, color: 'bg-arbiter-red' },
  ];

  return (
    <div className="mt-5 space-y-3">
      {bars.map((b) => (
        <div key={b.label} className="space-y-1">
          <div className="flex justify-between font-mono text-[10px]">
            <span className="text-arbiter-text-dim tracking-widest">{b.label}</span>
            <span className={`font-bold ${b.value >= 0 ? 'text-arbiter-text-muted' : 'text-arbiter-red-bright'}`}>
              {b.value > 0 ? `+${b.value}` : b.value}
            </span>
          </div>
          <div className="h-1 bg-arbiter-border">
            <div className={`h-full ${b.color}`} style={{ width: `${(Math.abs(b.value) / b.max) * 100}%` }} />
          </div>
        </div>
      ))}
      <div className="flex justify-between font-mono text-[11px] pt-2 border-t border-arbiter-border-subtle">
        <span className="text-arbiter-text-dim tracking-widest">FINAL</span>
        <span className="text-arbiter-text font-extrabold">106 / 110</span>
      </div>
    </div>
  );
}

/* ─────────── TECH BADGE ─────────── */
function TechBadge({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-2 border border-arbiter-border px-3 py-1.5 bg-arbiter-surface font-mono text-[11px] text-arbiter-text-muted hover:border-arbiter-red/40 hover:text-arbiter-text transition-colors">
      <Icon className="w-3.5 h-3.5 text-arbiter-text-dim" />
      {label}
    </div>
  );
}

/* ═══════════════════════════════════════════
   LANDING PAGE
   ═══════════════════════════════════════════ */
export default function LandingPage() {
  const navigate = useNavigate();
  const heroRef = useRef(null);
  const isHeroInView = useInView(heroRef, { once: true });

  return (
    <div className="min-h-screen bg-arbiter-bg text-arbiter-text relative overflow-x-hidden">
      {/* ── NAVIGATION ── */}
      <nav className="border-b border-arbiter-border sticky top-0 z-50 bg-arbiter-bg/95 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-arbiter-red-bright" />
            <span className="font-mono font-extrabold text-[15px] tracking-tight">THE ARBITER</span>
            <span className="hidden sm:inline text-[10px] text-arbiter-text-dim font-mono border border-arbiter-border px-1.5 py-0.5 tracking-widest">
              v2.1.0
            </span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#features" className="hidden md:inline text-[13px] text-arbiter-text-muted hover:text-arbiter-text transition font-medium tracking-wide">
              Capabilities
            </a>
            <button
              onClick={() => navigate('/dashboard')}
              className="text-[13px] text-arbiter-text-muted hover:text-arbiter-text transition font-medium tracking-wide"
            >
              Dashboard
            </button>
            <div className="w-px h-4 bg-arbiter-border hidden md:block" />
            <button
              onClick={() => navigate('/run')}
              className="font-mono text-[12px] font-bold text-arbiter-bg bg-arbiter-text px-4 py-1.5 hover:bg-arbiter-text/90 transition tracking-wide"
            >
              LAUNCH →
            </button>
          </div>
        </div>
      </nav>

      {/* ── HERO SECTION ── */}
      <section className="relative">
        {/* Grid background */}
        <div className="absolute inset-0 grid-pattern opacity-50" />
        {/* Red gradient glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-arbiter-red/8 rounded-full blur-[80px] pointer-events-none" />

        <motion.div
          ref={heroRef}
          initial="hidden"
          animate={isHeroInView ? 'visible' : 'hidden'}
          variants={stagger}
          className="relative z-10 max-w-6xl mx-auto px-5 pt-20 pb-16 md:pt-28 md:pb-20"
        >
          {/* Badge */}
          <motion.div variants={fadeUp} className="flex items-center gap-2 mb-8">
            <span className="font-mono text-[10px] font-bold text-arbiter-red-bright border border-arbiter-red/30 px-2 py-0.5 tracking-[0.2em] bg-arbiter-red/5">
              RIFT 2026
            </span>
            <span className="font-mono text-[10px] text-arbiter-text-dim tracking-[0.15em]">
              AI/ML DEVOPS AUTOMATION TRACK
            </span>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
            {/* Left: Copy */}
            <div>
              <motion.h1 variants={fadeUp} className="text-4xl md:text-5xl lg:text-[56px] font-extrabold leading-[1.05] tracking-tight">
                Cut debugging
                <br />
                time by{' '}
                <span className="relative inline-block">
                  <span className="text-arbiter-red-bright">40–60%</span>
                  <span className="absolute -bottom-1 left-0 w-full h-[2px] bg-arbiter-red/40" />
                </span>
              </motion.h1>

              <motion.p variants={fadeUp} className="mt-6 text-[15px] md:text-[16px] text-arbiter-text-muted leading-relaxed max-w-lg font-light">
                The Arbiter autonomously clones your repo, identifies failing tests,
                generates fixes through multi-agent consensus, and verifies everything
                passes—before you finish your coffee.
              </motion.p>

              {/* CTA */}
              <motion.div variants={fadeUp} className="mt-8 flex flex-col sm:flex-row items-start gap-3">
                <button
                  onClick={() => navigate('/run')}
                  className="group flex items-center gap-2.5 bg-arbiter-red hover:bg-arbiter-red-bright text-white font-mono font-bold text-[13px] px-6 py-3 tracking-wide transition-all glow-red"
                >
                  Launch Arbiter
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
                <a
                  href="#features"
                  className="font-mono text-[12px] text-arbiter-text-muted border border-arbiter-border px-5 py-3 hover:border-arbiter-text-dim hover:text-arbiter-text transition tracking-wide"
                >
                  How it works
                </a>
              </motion.div>

              {/* Stats row */}
              <motion.div variants={fadeUp} className="mt-12 flex items-center gap-8 md:gap-12">
                <StatNumber value="4,721" label="Runs Completed" />
                <div className="w-px h-10 bg-arbiter-border" />
                <StatNumber value="94.2" suffix="%" label="Success Rate" />
                <div className="w-px h-10 bg-arbiter-border hidden sm:block" />
                <div className="hidden sm:block">
                  <StatNumber value="2m 34s" label="Avg Heal Time" />
                </div>
              </motion.div>
            </div>

            {/* Right: Terminal */}
            <motion.div variants={fadeIn} className="lg:mt-4">
              <VisualTerminal />
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* ── FEATURE BENTO GRID ── */}
      <section id="features" className="relative border-t border-arbiter-border">
        <div className="max-w-6xl mx-auto px-5 py-16 md:py-24">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-80px' }}
            variants={stagger}
          >
            <motion.div variants={fadeUp} className="mb-12">
              <span className="font-mono text-[10px] text-arbiter-red-bright tracking-[0.2em] font-bold">CAPABILITIES</span>
              <h2 className="text-2xl md:text-3xl font-extrabold mt-2 tracking-tight">How The Arbiter heals your pipeline</h2>
            </motion.div>

            {/* Bento Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-arbiter-border">
              {/* Tile A: Multi-Agent Consensus */}
              <BentoTile
                icon={Users}
                title="Multi-Agent Consensus"
                description="Three specialized agents—Arbiter, Coder, and Auditor—collaborate through a reasoning loop. No single point of failure."
                span="lg:col-span-2"
              >
                <AgentFlowDiagram />
              </BentoTile>

              {/* Tile B: Self-Healing Workflows */}
              <BentoTile
                icon={GitBranch}
                title="Self-Healing Workflows"
                description="Every fix is committed with the [AI-AGENT] prefix, fully traceable. Automatic branch creation and PR submission."
              >
                <CommitLog />
              </BentoTile>

              {/* Tile C: Real-time Scoring */}
              <BentoTile
                icon={BarChart3}
                title="Real-Time Scoring"
                description="Base score of 100, speed bonus (+10 under 5 min), efficiency penalty (-2 per commit over 20). Transparent and deterministic."
              >
                <ScoringVisual />
              </BentoTile>

              {/* Tile D: CI/CD Integration */}
              <BentoTile
                icon={Activity}
                title="Pipeline Integration"
                description="Plugs into GitHub Actions, GitLab CI, or any webhook-driven pipeline. One config, zero disruption."
              >
                <div className="mt-5 grid grid-cols-3 gap-2">
                  {['GitHub Actions', 'Docker', 'Webhooks'].map((t) => (
                    <div key={t} className="border border-arbiter-border-subtle px-2 py-1.5 text-center font-mono text-[10px] text-arbiter-text-dim bg-arbiter-bg tracking-wider">
                      {t}
                    </div>
                  ))}
                </div>
              </BentoTile>

              {/* Tile E: Uptime */}
              <BentoTile
                icon={Zap}
                title="Sub-5 Minute Resolution"
                description="Average heal time of 2m 34s. The speed bonus kicks in automatically when the agent resolves faster than the threshold."
              >
                <div className="mt-5 flex items-end gap-1 h-12">
                  {[40, 65, 35, 80, 55, 90, 45, 70, 85, 60, 75, 95].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-arbiter-red/30 hover:bg-arbiter-red/60 transition-colors"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
              </BentoTile>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── COMPLIANCE & TRUST ── */}
      <section className="border-t border-arbiter-border">
        <div className="max-w-6xl mx-auto px-5 py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            {/* Badges */}
            <div className="flex items-center gap-4">
              <div className="border border-arbiter-red/40 bg-arbiter-red/5 px-4 py-2 flex items-center gap-2">
                <Shield className="w-4 h-4 text-arbiter-red-bright" />
                <div>
                  <div className="font-mono text-[11px] font-bold text-arbiter-red-bright tracking-widest">RIFT 2026</div>
                  <div className="text-[9px] text-arbiter-text-dim">Hackathon Entry</div>
                </div>
              </div>
              <div className="border border-arbiter-border bg-arbiter-surface px-4 py-2 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-arbiter-text-dim" />
                <div>
                  <div className="font-mono text-[11px] font-bold text-arbiter-text-muted tracking-widest">AGENTIC DEVOPS</div>
                  <div className="text-[9px] text-arbiter-text-dim">AI/ML Track</div>
                </div>
              </div>
            </div>

            {/* CTA */}
            <button
              onClick={() => navigate('/dashboard')}
              className="group flex items-center gap-2 font-mono text-[12px] font-bold text-arbiter-text border border-arbiter-border px-5 py-2.5 hover:border-arbiter-red hover:bg-arbiter-red/5 transition tracking-wide"
            >
              Open Dashboard
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition" />
            </button>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-arbiter-border bg-arbiter-surface py-8">
        <div className="max-w-6xl mx-auto px-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-arbiter-red-bright" />
            <span className="font-mono font-bold text-[12px] tracking-tight text-arbiter-text">THE ARBITER</span>
          </div>
          <span className="font-mono text-[10px] text-arbiter-text-dim tracking-wider text-center sm:text-right">
            © 2026 RIFT HACKATHON · AI/ML DEVOPS AUTOMATION
          </span>
        </div>
      </footer>
    </div>
  );
}
