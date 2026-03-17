// Dashboard data (from GET /dashboard/data and SSE stream)
export interface DashboardData {
  timestamp: string;
  system: SystemStats;
  channels: ChannelStats;
  heartbeat: HeartbeatStats;
  sessions: SessionStats;
  scheduler_running: boolean;
}

export interface SystemStats {
  cpu_percent: number;
  memory_percent: number;
  memory_available_gb: number;
  disk_free_gb: number;
  disk_percent: number;
  process_memory_mb: number;
  uptime_seconds: number;
}

export interface ChannelStats {
  total_channels: number;
  active_channels_24h: number;
  recent_channels: { channel: string; last_active: string }[];
  total_messages: number;
  messages_today: number;
}

export interface HeartbeatStats {
  enabled: boolean;
  interval: number;
  tasks: TaskInfo[];
  recent_logs: HeartbeatLog[];
}

export interface TaskInfo {
  name: string;
  enabled: boolean;
  schedule: string | null;
  last_run: string | null;
  due?: boolean;
}

export interface HeartbeatLog {
  id: number;
  timestamp: string;
  task_name: string;
  result: string;
}

export interface SessionStats {
  active: number;
  sessions: ActiveSession[];
}

export interface ActiveSession {
  name: string;
  started_at: number;
  elapsed_seconds: number;
  model: string;
  prompt_preview: string;
  workspace: string;
  pid: number | null;
  progress: string | null;
}

// Channel list (from GET /channels)
export interface ChannelInfo {
  channel: string;
  message_count: number;
  last_active: string;
}

// Message history (from GET /history/{channel})
export interface HistoryMessage {
  id: number;
  timestamp: string;
  message: string;
  response: string | null;
  model_used: string | null;
  tokens_used: number | null;
}

// Webhook response (from POST /webhook)
export interface WebhookResponse {
  status: string;
  response?: string;
  session_id?: string;
  metadata?: {
    channel: string;
    timestamp: string;
  };
}
