import { useState, useRef, useEffect } from 'react';
import type { DashboardData, HistoryMessage } from '../types/api';
import { Toggle } from '../components/Toggle';
import { TimeAgo } from '../components/TimeAgo';
import { updateTask, runTask, getTaskHistory, deleteMessage } from '../api/client';

interface TasksPageProps {
  data: DashboardData;
}

export function TasksPage({ data }: TasksPageProps) {
  const tasks = data.heartbeat.tasks;
  const [runningTask, setRunningTask] = useState<string | null>(null);
  const [historyTask, setHistoryTask] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  async function handleToggle(name: string, enabled: boolean) {
    await updateTask(name, { enabled });
  }

  async function handleRun(name: string) {
    setRunningTask(name);
    try {
      await runTask(name);
    } finally {
      setTimeout(() => setRunningTask(null), 2000);
    }
  }

  async function handleShowHistory(name: string) {
    if (historyTask === name) {
      setHistoryTask(null);
      return;
    }
    setHistoryTask(name);
    setLoadingHistory(true);
    try {
      const h = await getTaskHistory(name);
      setHistory(h);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleDeleteHistoryEntry(id: number) {
    await deleteMessage('heartbeat', id);
    setHistory((prev) => prev.filter((h) => h.id !== id));
  }

  return (
    <div>
      {/* Task table */}
      <div className="bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-primary text-text-muted text-xs uppercase tracking-wide">
              <th className="text-left px-4 py-3 font-semibold">Task</th>
              <th className="text-left px-4 py-3 font-semibold">Schedule</th>
              <th className="text-center px-4 py-3 font-semibold">Enabled</th>
              <th className="text-left px-4 py-3 font-semibold">Last Run</th>
              <th className="text-right px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.name} className="border-b border-border-secondary hover:bg-bg-tertiary/50">
                <td className="px-4 py-3 text-text-primary font-medium">{task.name}</td>
                <td className="px-4 py-3">
                  <EditableSchedule name={task.name} schedule={task.schedule} />
                </td>
                <td className="px-4 py-3 text-center">
                  <Toggle checked={task.enabled} onChange={(v) => handleToggle(task.name, v)} />
                </td>
                <td className="px-4 py-3 text-text-muted text-xs">
                  <TimeAgo timestamp={task.last_run} />
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button
                    onClick={() => handleRun(task.name)}
                    disabled={runningTask === task.name}
                    className="px-2.5 py-1 text-xs rounded border border-border-primary text-text-secondary hover:bg-bg-tertiary disabled:opacity-50 cursor-pointer"
                  >
                    {runningTask === task.name ? 'Running...' : 'Run Now'}
                  </button>
                  <button
                    onClick={() => handleShowHistory(task.name)}
                    className={`px-2.5 py-1 text-xs rounded border border-border-primary cursor-pointer ${
                      historyTask === task.name
                        ? 'bg-bg-tertiary text-text-primary'
                        : 'text-text-secondary hover:bg-bg-tertiary'
                    }`}
                  >
                    History
                  </button>
                </td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-muted">
                  No tasks found in workspace/.claude/tasks/
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* History panel */}
      {historyTask && (
        <div className="mt-4 bg-bg-secondary border border-border-primary rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-text-primary">
              History: {historyTask}
            </h3>
            <button
              onClick={() => handleShowHistory(historyTask)}
              className="text-xs text-text-muted hover:text-text-secondary cursor-pointer"
            >
              Refresh
            </button>
          </div>
          {loadingHistory ? (
            <p className="text-sm text-text-muted">Loading...</p>
          ) : history.length === 0 ? (
            <p className="text-sm text-text-muted">No run history</p>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {history.map((entry) => (
                <div key={entry.id} className="text-sm border-b border-border-secondary pb-3 last:border-0">
                  <div className="flex justify-between items-start">
                    <span className="text-xs text-text-muted">
                      <TimeAgo timestamp={entry.timestamp} />
                      {entry.model_used && <span className="ml-2">{entry.model_used}</span>}
                      {entry.tokens_used && <span className="ml-2">{entry.tokens_used} tokens</span>}
                    </span>
                    <button
                      onClick={() => handleDeleteHistoryEntry(entry.id)}
                      className="text-xs text-danger hover:text-danger-hover cursor-pointer"
                    >
                      Delete
                    </button>
                  </div>
                  {entry.response && (
                    <div className="text-text-secondary mt-1 text-xs max-h-24 overflow-hidden">
                      {entry.response}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EditableSchedule({ name, schedule }: { name: string; schedule: string | null }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(schedule || '');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  async function save() {
    setEditing(false);
    const newSchedule = value.trim() || 'on-demand';
    if (newSchedule !== (schedule || 'on-demand')) {
      await updateTask(name, { schedule: value.trim() || '' });
    }
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === 'Enter') inputRef.current?.blur();
          if (e.key === 'Escape') {
            setValue(schedule || '');
            setEditing(false);
          }
        }}
        placeholder="e.g. every morning"
        className="w-full px-2 py-1 text-sm rounded border border-accent bg-bg-primary text-text-secondary focus:outline-none"
      />
    );
  }

  return (
    <span
      onClick={() => {
        setValue(schedule === 'on-demand' ? '' : schedule || '');
        setEditing(true);
      }}
      className="text-text-secondary cursor-pointer hover:text-accent"
    >
      {schedule || 'on-demand'}
    </span>
  );
}
