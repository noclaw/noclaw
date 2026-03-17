import type {
  DashboardData,
  ChannelInfo,
  HistoryMessage,
  TaskInfo,
  WebhookResponse,
} from '../types/api';

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string>),
  };

  const apiKey = localStorage.getItem('noclaw_api_key');
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const resp = await fetch(url, { ...opts, headers });

  if (resp.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, body.detail || resp.statusText);
  }

  return resp.json();
}

// Dashboard
export async function getDashboardData(): Promise<DashboardData> {
  return apiFetch('/dashboard/data');
}

export async function login(password: string): Promise<void> {
  await apiFetch<{ status: string }>('/dashboard/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch<{ status: string }>('/dashboard/logout', {
    method: 'POST',
  });
}

// Channels & History
export async function getChannels(): Promise<ChannelInfo[]> {
  const data = await apiFetch<{ channels: ChannelInfo[] }>('/channels');
  return data.channels;
}

export async function getHistory(channel: string, limit = 50): Promise<HistoryMessage[]> {
  const data = await apiFetch<{ history: HistoryMessage[] }>(
    `/history/${encodeURIComponent(channel)}?limit=${limit}`
  );
  return data.history;
}

export async function deleteMessage(channel: string, id: number): Promise<void> {
  await apiFetch(`/history/${encodeURIComponent(channel)}/${id}`, { method: 'DELETE' });
}

export async function clearChannel(channel: string): Promise<void> {
  await apiFetch(`/history/${encodeURIComponent(channel)}`, { method: 'DELETE' });
}

// Tasks
export async function getTaskDetail(name: string): Promise<TaskInfo> {
  return apiFetch(`/tasks/${encodeURIComponent(name)}`);
}

export async function updateTask(name: string, patch: { enabled?: boolean; schedule?: string }): Promise<void> {
  await apiFetch(`/tasks/${encodeURIComponent(name)}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export async function runTask(name: string): Promise<{ response: string }> {
  return apiFetch(`/tasks/${encodeURIComponent(name)}/run`, { method: 'POST' });
}

export async function getTaskHistory(name: string): Promise<HistoryMessage[]> {
  const data = await apiFetch<{ history: HistoryMessage[] }>(
    `/tasks/${encodeURIComponent(name)}/history`
  );
  return data.history;
}

// Heartbeat
export async function enableHeartbeat(): Promise<void> {
  await apiFetch('/heartbeat/enable', { method: 'POST' });
}

export async function disableHeartbeat(): Promise<void> {
  await apiFetch('/heartbeat/disable', { method: 'POST' });
}

// Sessions
export async function killSession(name: string): Promise<void> {
  await apiFetch(`/sessions/${encodeURIComponent(name)}/kill`, { method: 'POST' });
}

export async function getSessionLogs(name: string): Promise<{ output: string; status: string }> {
  return apiFetch(`/sessions/${encodeURIComponent(name)}/logs`);
}

// Agent
export async function sendMessage(body: {
  message: string;
  channel?: string;
  model_hint?: string;
  resume?: string;
}): Promise<WebhookResponse> {
  return apiFetch('/webhook', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export { ApiError };
