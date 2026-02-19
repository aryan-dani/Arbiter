import { useState } from 'react';
import { Rocket, Loader2, RotateCcw } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function InputForm() {
  const {
    repoUrl, teamName, leaderName,
    setRepoUrl, setTeamName, setLeaderName,
    runAgent, isRunning, runComplete, reset,
  } = useAgentStore();

  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!repoUrl.trim() || !/^https?:\/\/(www\.)?github\.com\/.+\/.+/i.test(repoUrl.trim()))
      e.repoUrl = 'Enter a valid GitHub repository URL';
    if (!teamName.trim()) e.teamName = 'Team name is required';
    if (!leaderName.trim()) e.leaderName = 'Leader name is required';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) runAgent();
  };

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800/60 backdrop-blur-sm border border-slate-700 rounded-2xl p-6 md:p-8 shadow-lg">
      <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
        <Rocket className="w-5 h-5 text-blue-400" />
        Agent Configuration
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Repo URL */}
        <div className="md:col-span-3">
          <label className="block text-sm font-medium text-slate-300 mb-1.5">GitHub Repository URL</label>
          <input
            type="url"
            placeholder="https://github.com/owner/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            disabled={isRunning || runComplete}
            className={`w-full rounded-lg bg-slate-900/70 border px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition disabled:opacity-50 ${
              errors.repoUrl ? 'border-red-500' : 'border-slate-600'
            }`}
          />
          {errors.repoUrl && <p className="text-red-400 text-xs mt-1">{errors.repoUrl}</p>}
        </div>

        {/* Team Name */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">Team Name</label>
          <input
            type="text"
            placeholder="Team Alpha"
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            disabled={isRunning || runComplete}
            className={`w-full rounded-lg bg-slate-900/70 border px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition disabled:opacity-50 ${
              errors.teamName ? 'border-red-500' : 'border-slate-600'
            }`}
          />
          {errors.teamName && <p className="text-red-400 text-xs mt-1">{errors.teamName}</p>}
        </div>

        {/* Leader Name */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">Team Leader Name</label>
          <input
            type="text"
            placeholder="Jane Doe"
            value={leaderName}
            onChange={(e) => setLeaderName(e.target.value)}
            disabled={isRunning || runComplete}
            className={`w-full rounded-lg bg-slate-900/70 border px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition disabled:opacity-50 ${
              errors.leaderName ? 'border-red-500' : 'border-slate-600'
            }`}
          />
          {errors.leaderName && <p className="text-red-400 text-xs mt-1">{errors.leaderName}</p>}
        </div>

        {/* Buttons */}
        <div className="flex items-end gap-3">
          {!runComplete ? (
            <button
              type="submit"
              disabled={isRunning}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-2.5 px-6 rounded-lg transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-md hover:shadow-blue-500/25"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running Agent…
                </>
              ) : (
                <>
                  <Rocket className="w-4 h-4" />
                  Run Agent
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              onClick={reset}
              className="w-full flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-2.5 px-6 rounded-lg transition-all shadow-md"
            >
              <RotateCcw className="w-4 h-4" />
              New Run
            </button>
          )}
        </div>
      </div>
    </form>
  );
}
