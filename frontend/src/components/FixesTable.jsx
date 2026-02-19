import { FileCode, CheckCircle2, XCircle } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

const BUG_COLORS = {
  LINTING: 'bg-arbiter-red/20 text-arbiter-red-bright',
  SYNTAX: 'bg-arbiter-amber/20 text-arbiter-amber',
  LOGIC: 'bg-arbiter-text-dim/20 text-arbiter-text-muted',
  TYPE_ERROR: 'bg-arbiter-red-bright/20 text-arbiter-red-bright',
  IMPORT: 'bg-arbiter-green/20 text-arbiter-green',
  INDENTATION: 'bg-arbiter-amber/20 text-arbiter-amber',
};

export default function FixesTable() {
  const { runData } = useAgentStore();
  if (!runData) return null;

  return (
    <div className="animate-slide-in bg-arbiter-surface border border-arbiter-border p-6 shadow-lg">
      <h2 className="text-lg font-bold text-arbiter-text mb-5 flex items-center gap-2 font-mono">
        <FileCode className="w-5 h-5 text-arbiter-green" />
        Fixes Applied
        <span className="ml-auto text-xs font-normal text-arbiter-text-dim">{runData.fixes.length} total</span>
      </h2>

      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-arbiter-text-dim border-b border-arbiter-border font-mono">
              <th className="pb-3 pr-4">#</th>
              <th className="pb-3 pr-4">File</th>
              <th className="pb-3 pr-4">Bug Type</th>
              <th className="pb-3 pr-4">Line</th>
              <th className="pb-3 pr-4">Commit Message</th>
              <th className="pb-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-arbiter-border/50">
            {runData.fixes.map((fix) => (
              <tr key={fix.id} className="group hover:bg-arbiter-bg/50 transition">
                <td className="py-3 pr-4 text-arbiter-text-dim font-mono text-xs">{fix.id}</td>
                <td className="py-3 pr-4 text-arbiter-text font-mono text-xs">{fix.file}</td>
                <td className="py-3 pr-4">
                  <span className={`inline-block px-2 py-0.5 text-xs font-semibold ${BUG_COLORS[fix.bugType] || 'bg-arbiter-border text-arbiter-text-muted'}`}>
                    {fix.bugType}
                  </span>
                </td>
                <td className="py-3 pr-4 text-arbiter-text-muted font-mono text-xs">L{fix.lineNumber}</td>
                <td className="py-3 pr-4 text-arbiter-text-muted text-xs max-w-xs truncate">{fix.commitMessage}</td>
                <td className="py-3 text-right">
                  {fix.status === 'Fixed' ? (
                    <span className="inline-flex items-center gap-1 text-arbiter-green text-xs font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Fixed
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-arbiter-red-bright text-xs font-semibold">
                      <XCircle className="w-3.5 h-3.5" /> Failed
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {runData.fixes.map((fix) => (
          <div key={fix.id} className="bg-arbiter-bg border border-arbiter-border p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-arbiter-text-dim">#{fix.id}</span>
              {fix.status === 'Fixed' ? (
                <span className="inline-flex items-center gap-1 text-arbiter-green text-xs font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Fixed
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-arbiter-red-bright text-xs font-semibold">
                  <XCircle className="w-3.5 h-3.5" /> Failed
                </span>
              )}
            </div>
            <p className="text-sm text-arbiter-text font-mono">{fix.file} <span className="text-arbiter-text-dim">: L{fix.lineNumber}</span></p>
            <span className={`inline-block px-2 py-0.5 text-xs font-semibold ${BUG_COLORS[fix.bugType]}`}>
              {fix.bugType}
            </span>
            <p className="text-xs text-arbiter-text-dim truncate">{fix.commitMessage}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
