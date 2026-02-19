import { Outlet } from 'react-router-dom';

import TopBar from './TopBar';

export default function Layout() {
    return (
        <div className="flex h-screen bg-arbiter-bg text-arbiter-text overflow-hidden">


            {/* Main area */}
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                {/* Top bar */}
                <TopBar />

                {/* Scrollable content */}
                <div className="flex-1 overflow-y-auto">
                    <Outlet />
                </div>
            </div>
        </div>
    );
}
