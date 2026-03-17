import { NavLink, Outlet } from 'react-router-dom';
import type { DashboardData } from '../types/api';

interface LayoutProps {
  connected: boolean;
  data: DashboardData | null;
}

const tabs = [
  { to: '/', label: 'Overview' },
  { to: '/tasks', label: 'Tasks' },
  { to: '/conversations', label: 'Conversations' },
  { to: '/agent', label: 'Agent' },
];

export function Layout({ connected, data }: LayoutProps) {
  return (
    <div className="max-w-[1400px] mx-auto px-5 py-5">
      {/* Header */}
      <header className="mb-5 pb-4 border-b border-border-primary">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-accent">NoClaw</h1>
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold text-white ${
              connected ? 'bg-success' : 'bg-danger'
            }`}
          >
            {connected && (
              <span
                className="w-1.5 h-1.5 bg-white rounded-full"
                style={{ animation: 'pulse-dot 2s ease-in-out infinite' }}
              />
            )}
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
        {data && (
          <div className="text-xs text-text-muted mt-1">
            {data.sessions.active} active session{data.sessions.active !== 1 ? 's' : ''}
            {' \u00B7 '}
            {data.channels.messages_today} messages today
          </div>
        )}
      </header>

      {/* Tab bar */}
      <nav className="flex border-b border-border-primary mb-5">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === '/'}
            className={({ isActive }) =>
              `px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? 'text-text-primary border-accent'
                  : 'text-text-muted border-transparent hover:text-text-secondary'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      {/* Page content */}
      <Outlet />
    </div>
  );
}
