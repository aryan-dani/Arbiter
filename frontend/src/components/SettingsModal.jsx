import { X } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function SettingsModal({ open, onClose }) {
  const { repoUrl, teamName, leaderName, setRepoUrl, setTeamName, setLeaderName, isRunning } = useAgentStore();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="bg-arbiter-surface border border-arbiter-border shadow-2xl w-full max-w-lg p-6 animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-arbiter-text font-mono">Agent Configuration</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center hover:bg-arbiter-bg transition"
          >
            <X className="w-4 h-4 text-arbiter-text-dim" />
          </button>
        </div>

        {/* Fields */}
        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-arbiter-text-dim uppercase tracking-wider mb-1.5 font-mono">
              GitHub Repository URL
            </label>
            <input
              type="url"
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              disabled={isRunning}
              className="w-full bg-arbiter-bg border border-arbiter-border px-4 py-2.5 text-[13px] text-arbiter-text placeholder-arbiter-text-dim focus:outline-none focus:ring-1 focus:ring-arbiter-red focus:border-arbiter-red transition disabled:opacity-50 font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-semibold text-arbiter-text-dim uppercase tracking-wider mb-1.5 font-mono">
                Team Name
              </label>
              <input
                type="text"
                placeholder="Team Alpha"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                disabled={isRunning}
                className="w-full bg-arbiter-bg border border-arbiter-border px-4 py-2.5 text-[13px] text-arbiter-text placeholder-arbiter-text-dim focus:outline-none focus:ring-1 focus:ring-arbiter-red focus:border-arbiter-red transition disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-arbiter-text-dim uppercase tracking-wider mb-1.5 font-mono">
                Leader Name
              </label>
              <input
                type="text"
                placeholder="Jane Doe"
                value={leaderName}
                onChange={(e) => setLeaderName(e.target.value)}
                disabled={isRunning}
                className="w-full bg-arbiter-bg border border-arbiter-border px-4 py-2.5 text-[13px] text-arbiter-text placeholder-arbiter-text-dim focus:outline-none focus:ring-1 focus:ring-arbiter-red focus:border-arbiter-red transition disabled:opacity-50"
              />
            </div>
          </div>
        </div>

        {/* Save button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="bg-arbiter-red hover:bg-arbiter-red-bright text-white text-[13px] font-mono font-bold px-6 py-2.5 transition-all tracking-wide"
          >
            Save & Close
          </button>
        </div>
      </div>
    </div>
  );
}
