import { Shield, Zap, CheckCircle, XCircle, BarChart3 } from 'lucide-react';

const NAV_ITEMS = [
  { icon: Zap, status: 'active', label: 'Dashboard' },
  { icon: CheckCircle, status: 'success', label: 'Passed' },
  { icon: XCircle, status: 'error', label: 'Failed' },
  { icon: BarChart3, status: 'success', label: 'Analytics' },
];

export default function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col items-center w-[52px] bg-arbiter-bg border-r border-arbiter-border py-4 gap-3 shrink-0">
      {/* Logo */}
      <div className="w-9 h-9 flex items-center justify-center border border-arbiter-red bg-arbiter-red/10 mb-1">
        <Shield className="w-5 h-5 text-white" />
      </div>

      {/* Vertical label */}
      <div className="flex-1 flex items-start pt-2">
        <span
          className="text-[10px] font-bold tracking-[0.25em] text-arbiter-text-dim uppercase font-mono"
          style={{ writingMode: 'vertical-lr' }}
        >
          ARBITER
        </span>
      </div>

      {/* Nav Icons */}
      <div className="flex flex-col items-center gap-2">
        {NAV_ITEMS.map((item, i) => (
          <button
            key={i}
            className="relative group w-9 h-9 flex items-center justify-center hover:bg-arbiter-surface transition"
            title={item.label}
          >
            <item.icon className={`w-[18px] h-[18px] ${
              item.status === 'active' ? 'text-arbiter-red-bright' :
              item.status === 'success' ? 'text-slate-400' :
              'text-slate-400'
            }`} />
            {/* Status dot */}
            {item.status !== 'active' && (
              <span className={`absolute -left-0.5 top-1/2 -translate-y-1/2 w-[5px] h-[5px] rounded-full ${
                item.status === 'success' ? 'bg-green-500' : 'bg-red-500'
              }`} />
            )}
          </button>
        ))}
      </div>
    </aside>
  );
}
