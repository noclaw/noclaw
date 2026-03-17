import { type FormEvent, useState } from 'react';
import type { DashboardData } from '../types/api';
import { Card } from '../components/Card';
import { sendMessage, runTask, killSession } from '../api/client';

interface AgentPageProps {
  data: DashboardData;
}

export function AgentPage({ data }: AgentPageProps) {
  const [message, setMessage] = useState('');
  const [channel, setChannel] = useState('dashboard');
  const [model, setModel] = useState('');
  const [resumeId, setResumeId] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState('');

  const [selectedTask, setSelectedTask] = useState('');
  const [runningTask, setRunningTask] = useState(false);
  const [taskResult, setTaskResult] = useState('');

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setSending(true);
    setResult('');
    try {
      const body: { message: string; channel?: string; model_hint?: string; resume?: string } = {
        message,
        channel: channel || 'dashboard',
      };
      if (model) body.model_hint = model;
      if (resumeId) body.resume = resumeId;
      const resp = await sendMessage(body);
      setResult(resp.response || JSON.stringify(resp));
      if (resp.session_id) {
        setResumeId(resp.session_id);
      }
    } catch (err) {
      setResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSending(false);
    }
  }

  async function handleRunTask() {
    if (!selectedTask) return;
    setRunningTask(true);
    setTaskResult('');
    try {
      const resp = await runTask(selectedTask);
      setTaskResult(resp.response || 'Task completed');
    } catch (err) {
      setTaskResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRunningTask(false);
    }
  }

  async function handleKill(name: string) {
    if (!confirm(`Kill session "${name}"?`)) return;
    await killSession(name);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Send Message */}
      <Card title="Send Message">
        <form onSubmit={handleSend} className="space-y-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            placeholder="Enter a message..."
            className="w-full px-3 py-2 rounded-md border border-border-primary bg-bg-primary text-text-secondary text-sm resize-y focus:outline-none focus:border-accent"
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-muted mb-1">Channel</label>
              <input
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-md border border-border-primary bg-bg-primary text-text-secondary text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">Model</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-md border border-border-primary bg-bg-primary text-text-secondary text-sm focus:outline-none focus:border-accent"
              >
                <option value="">Default</option>
                <option value="haiku">Haiku</option>
                <option value="sonnet">Sonnet</option>
                <option value="opus">Opus</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Resume Session ID</label>
            <input
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
              placeholder="Optional — auto-filled after sending"
              className="w-full px-2.5 py-1.5 rounded-md border border-border-primary bg-bg-primary text-text-secondary text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <button
            type="submit"
            disabled={sending || !message.trim()}
            className="w-full py-2 rounded-md bg-success hover:bg-success-hover text-white text-sm font-semibold disabled:opacity-50 cursor-pointer"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </form>
        {result && (
          <div className="mt-3 p-3 bg-bg-primary border border-border-primary rounded-md text-sm text-text-secondary max-h-96 overflow-y-auto whitespace-pre-wrap">
            {result}
          </div>
        )}
      </Card>

      {/* Right column */}
      <div className="space-y-4">
        {/* Run Task */}
        <Card title="Run Task">
          <div className="flex gap-2">
            <select
              value={selectedTask}
              onChange={(e) => setSelectedTask(e.target.value)}
              className="flex-1 px-2.5 py-1.5 rounded-md border border-border-primary bg-bg-primary text-text-secondary text-sm focus:outline-none focus:border-accent"
            >
              <option value="">Select a task...</option>
              {data.heartbeat.tasks.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleRunTask}
              disabled={!selectedTask || runningTask}
              className="px-4 py-1.5 rounded-md bg-success hover:bg-success-hover text-white text-sm font-semibold disabled:opacity-50 cursor-pointer"
            >
              {runningTask ? 'Running...' : 'Run'}
            </button>
          </div>
          {taskResult && (
            <div className="mt-3 p-3 bg-bg-primary border border-border-primary rounded-md text-sm text-text-secondary max-h-48 overflow-y-auto whitespace-pre-wrap">
              {taskResult}
            </div>
          )}
        </Card>

        {/* Active Sessions */}
        <Card title="Active Sessions">
          {data.sessions.sessions.length === 0 ? (
            <p className="text-text-muted text-sm">No active sessions</p>
          ) : (
            <div className="space-y-3">
              {data.sessions.sessions.map((s) => (
                <div key={s.name} className="flex justify-between items-start text-sm">
                  <div>
                    <span className="text-text-primary font-medium">{s.name}</span>
                    <span className="text-text-muted ml-2 text-xs">
                      {s.model} &middot; {Math.floor(s.elapsed_seconds)}s
                    </span>
                    {s.progress && (
                      <div className="text-xs text-accent mt-0.5">{s.progress}</div>
                    )}
                  </div>
                  <button
                    onClick={() => handleKill(s.name)}
                    className="text-xs text-danger hover:text-danger-hover cursor-pointer"
                  >
                    Kill
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
