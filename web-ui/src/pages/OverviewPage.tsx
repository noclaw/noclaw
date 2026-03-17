import type { DashboardData } from '../types/api';
import { Card } from '../components/Card';
import { ProgressBar } from '../components/ProgressBar';
import { Toggle } from '../components/Toggle';
import { TimeAgo, formatUptime } from '../components/TimeAgo';
import { enableHeartbeat, disableHeartbeat, killSession } from '../api/client';

interface OverviewPageProps {
  data: DashboardData;
}

export function OverviewPage({ data }: OverviewPageProps) {
  const { system, channels, heartbeat, sessions } = data;

  async function handleHeartbeatToggle(enabled: boolean) {
    if (enabled) {
      await enableHeartbeat();
    } else {
      await disableHeartbeat();
    }
  }

  async function handleKill(name: string) {
    if (!confirm(`Kill session "${name}"?`)) return;
    await killSession(name);
  }

  return (
    <div className="space-y-5">
      {/* Stats row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* System */}
        <Card title="System">
          <ProgressBar value={system.cpu_percent} label="CPU" />
          <ProgressBar value={system.memory_percent} label="Memory" />
          <ProgressBar
            value={system.disk_percent}
            label="Disk"
            detail={`${system.disk_free_gb.toFixed(1)} GB free`}
          />
          <div className="flex justify-between text-xs text-text-muted mt-3 pt-3 border-t border-border-primary">
            <span>Process: {system.process_memory_mb.toFixed(0)} MB</span>
            <span>Uptime: {formatUptime(system.uptime_seconds)}</span>
          </div>
        </Card>

        {/* Channels */}
        <Card title="Channels">
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Total" value={channels.total_channels} />
            <Stat label="Active (24h)" value={channels.active_channels_24h} />
            <Stat label="Messages" value={channels.total_messages} />
            <Stat label="Today" value={channels.messages_today} />
          </div>
        </Card>

        {/* Heartbeat */}
        <Card
          title="Heartbeat"
          action={
            <Toggle
              checked={heartbeat.enabled}
              onChange={handleHeartbeatToggle}
            />
          }
        >
          <div className="grid grid-cols-2 gap-3">
            <Stat
              label="Status"
              value={data.scheduler_running ? 'Running' : 'Stopped'}
              color={data.scheduler_running ? 'text-live' : 'text-text-muted'}
            />
            <Stat label="Interval" value={`${heartbeat.interval}s`} />
            <Stat label="Tasks" value={heartbeat.tasks.length} />
            <Stat
              label="Enabled"
              value={heartbeat.tasks.filter((t) => t.enabled).length}
            />
          </div>
        </Card>

        {/* Sessions */}
        <Card title="Agent Sessions">
          {sessions.sessions.length === 0 ? (
            <p className="text-text-muted text-sm">No active sessions</p>
          ) : (
            <div className="space-y-3">
              {sessions.sessions.map((s) => (
                <div key={s.name} className="text-sm">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-text-primary font-medium">{s.name}</span>
                      <span className="text-text-muted ml-2 text-xs">{s.model}</span>
                    </div>
                    <button
                      onClick={() => handleKill(s.name)}
                      className="text-xs text-danger hover:text-danger-hover cursor-pointer"
                    >
                      Kill
                    </button>
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">
                    {Math.floor(s.elapsed_seconds)}s elapsed
                    {s.progress && (
                      <span className="ml-2 text-accent">{s.progress}</span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted truncate mt-0.5">
                    {s.prompt_preview}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Recent activity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Recent Channels */}
        <Card title="Recent Channels">
          {channels.recent_channels.length === 0 ? (
            <p className="text-text-muted text-sm">No recent activity</p>
          ) : (
            <div className="space-y-2">
              {channels.recent_channels.map((ch) => (
                <div key={ch.channel} className="flex justify-between text-sm">
                  <span className="text-text-secondary">{ch.channel}</span>
                  <span className="text-text-muted text-xs">
                    <TimeAgo timestamp={ch.last_active} />
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Recent Task Runs */}
        <Card title="Recent Task Runs">
          {heartbeat.recent_logs.length === 0 ? (
            <p className="text-text-muted text-sm">No recent runs</p>
          ) : (
            <div className="space-y-2">
              {heartbeat.recent_logs.map((log) => (
                <div key={log.id} className="text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary font-medium">{log.task_name}</span>
                    <span className="text-text-muted text-xs">
                      <TimeAgo timestamp={log.timestamp} />
                    </span>
                  </div>
                  <div className="text-xs text-text-muted truncate">{log.result}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div>
      <div className="text-xs text-text-muted">{label}</div>
      <div className={`text-lg font-semibold ${color || 'text-text-primary'}`}>{value}</div>
    </div>
  );
}
