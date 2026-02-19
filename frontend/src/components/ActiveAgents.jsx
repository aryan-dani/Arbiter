import { useRef, useEffect } from 'react';
import useAgentStore from '../store/useAgentStore';
import { Network, Terminal, Bug, Wrench, GitBranch, Trophy } from 'lucide-react';

const AGENTS = [
    { id: 'COORDINATOR', label: 'Coordinator', icon: Network },
    { id: 'DISCOVERY', label: 'Discovery', icon: Terminal },
    { id: 'TESTER', label: 'Tester', icon: Bug },
    { id: 'DEBUGGER', label: 'Debugger', icon: Bug },
    { id: 'FIXER', label: 'Fixer', icon: Wrench },
    { id: 'GIT', label: 'Git', icon: GitBranch },
    { id: 'SCORING', label: 'Scoring', icon: Trophy },
];

export default function ActiveAgents() {
    const { activeAgent, isRunning, runComplete } = useAgentStore();

    if (!isRunning && !runComplete) return null;

    return (
        <div className="bg-arbiter-surface border border-arbiter-border p-4 shadow-lg mb-3">
            <h3 className="text-xs font-bold text-arbiter-text-dim uppercase tracking-wider mb-3 font-mono">
                Active Runtime Nodes
            </h3>

            <div className="flex items-center justify-between relative">
                {/* Connection Line */}
                <div className="absolute top-1/2 left-0 w-full h-0.5 bg-arbiter-border -z-10" />

                {AGENTS.map((agent) => {
                    const isActive = activeAgent === agent.id;
                    const Icon = agent.icon;

                    return (
                        <div key={agent.id} className="flex flex-col items-center gap-2 bg-arbiter-surface px-1">
                            <div className={`
                           w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300
                           ${isActive
                                    ? 'bg-arbiter-green/20 border-arbiter-green shadow-[0_0_10px_rgba(34,197,94,0.4)] scale-110'
                                    : 'bg-arbiter-bg border-arbiter-border text-arbiter-text-dim'}
                       `}>
                                <Icon className={`w-4 h-4 ${isActive ? 'text-arbiter-green' : 'text-arbiter-text-dim'}`} />
                            </div>
                            <span className={`text-[10px] font-mono font-bold ${isActive ? 'text-arbiter-green' : 'text-arbiter-text-dim'}`}>
                                {agent.label}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
