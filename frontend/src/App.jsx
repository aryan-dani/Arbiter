import { useState } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import ActionBar from './components/ActionBar';
import StatsRow from './components/StatsRow';
import TerminalLog from './components/TerminalLog';
import PerformanceMetrics from './components/PerformanceMetrics';
import SummaryCard from './components/SummaryCard';
import ScorePanel from './components/ScorePanel';
import FixesTable from './components/FixesTable';
import Timeline from './components/Timeline';
import FinalStatus from './components/FinalStatus';
import SettingsModal from './components/SettingsModal';
import useAgentStore from './store/useAgentStore';

import ActiveAgents from './components/ActiveAgents';

function App() {
  const { runComplete, isRunning } = useAgentStore();
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="flex h-screen bg-arbiter-bg text-arbiter-text overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <TopBar />

        {/* Action bar */}
        <ActionBar onOpenSettings={() => setSettingsOpen(true)} />

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto">
          {/* Stats Row */}
          <StatsRow />

          {/* Active Agents Visualization */}
          <div className="px-5 pb-1">
            <ActiveAgents />
          </div>

          {/* Terminal + Performance Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 px-5 pb-4">
            <div className="lg:col-span-3">
              <TerminalLog />
            </div>
            <div className="lg:col-span-2">
              <PerformanceMetrics />
            </div>
          </div>

          {/* Post-run panels */}
          {runComplete && (
            <div className="px-5 pb-6 space-y-4">
              {/* Final Status */}
              <FinalStatus />

              {/* Summary + Score */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <SummaryCard />
                <ScorePanel />
              </div>

              <Timeline />
            </div>
          )}

          {/* Live Fixes Table (Running or Complete) */}
          {(runComplete || isRunning) && (
            <div className="px-5 pb-6">
              <FixesTable />
            </div>
          )}
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default App;
