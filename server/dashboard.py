#!/usr/bin/env python3
"""
NoClaw Control Panel

Tabbed dashboard with Server-Sent Events for real-time updates.
No heavy frameworks - just HTML, vanilla JS, and SSE.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import psutil
import os

logger = logging.getLogger(__name__)


class Dashboard:
    """NoClaw control panel dashboard"""

    def __init__(self, assistant):
        self.assistant = assistant
        logger.info("Dashboard initialized")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024 / 1024

            import time
            uptime_seconds = time.time() - process.create_time()

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "disk_percent": disk.percent,
                "process_memory_mb": process_memory,
                "uptime_seconds": uptime_seconds
            }
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}

    def get_channel_stats(self) -> Dict[str, Any]:
        """Get channel activity statistics"""
        try:
            import sqlite3

            with sqlite3.connect(self.assistant.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM channels")
                total_channels = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT COUNT(*) FROM channels
                    WHERE datetime(last_active) > datetime('now', '-1 day')
                """)
                active_channels = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT channel, last_active
                    FROM channels
                    WHERE datetime(last_active) > datetime('now', '-1 hour')
                    ORDER BY last_active DESC
                    LIMIT 10
                """)
                recent_channels = [
                    {"channel": row[0], "last_active": row[1]}
                    for row in cursor.fetchall()
                ]

                cursor.execute("SELECT COUNT(*) FROM message_history")
                total_messages = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT COUNT(*) FROM message_history
                    WHERE date(timestamp) = date('now')
                """)
                messages_today = cursor.fetchone()[0]

                return {
                    "total_channels": total_channels,
                    "active_channels_24h": active_channels,
                    "recent_channels": recent_channels,
                    "total_messages": total_messages,
                    "messages_today": messages_today
                }
        except Exception as e:
            logger.error(f"Failed to get channel stats: {e}")
            return {}

    def get_heartbeat_stats(self) -> Dict[str, Any]:
        """Get heartbeat statistics from message_history and task definitions"""
        try:
            import sqlite3

            with sqlite3.connect(self.assistant.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, timestamp, message, response
                    FROM message_history
                    WHERE channel = 'heartbeat'
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                recent_logs = [
                    {
                        "id": row[0],
                        "timestamp": row[1],
                        "task_name": row[2].split(']')[0].replace('[TASK: ', '') if row[2] and row[2].startswith('[TASK:') else 'unknown',
                        "result": row[3][:200] if row[3] else "N/A"
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    "enabled": self.assistant.heartbeat.enabled,
                    "interval": self.assistant.heartbeat.interval,
                    "tasks": self.assistant.heartbeat.list_tasks(),
                    "recent_logs": recent_logs,
                }
        except Exception as e:
            logger.error(f"Failed to get heartbeat stats: {e}")
            return {}

    def get_session_stats(self) -> Dict[str, Any]:
        """Get active agent session info"""
        try:
            from .agent import registry
            sessions = registry.list_active()
            return {
                "active": len(sessions),
                "sessions": [s.to_dict() for s in sessions],
            }
        except Exception:
            return {"active": 0, "sessions": []}

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": self.get_system_stats(),
            "channels": self.get_channel_stats(),
            "heartbeat": self.get_heartbeat_stats(),
            "sessions": self.get_session_stats(),
            "scheduler_running": hasattr(self.assistant, 'heartbeat') and self.assistant.heartbeat.running
        }

    def get_login_html(self) -> str:
        """Get login page HTML"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoClaw - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .login-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 32px; width: 340px; }
        h1 { font-size: 24px; color: #58a6ff; margin-bottom: 8px; }
        .subtitle { color: #8b949e; font-size: 13px; margin-bottom: 24px; }
        label { display: block; font-size: 13px; color: #8b949e; margin-bottom: 6px; }
        input { width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #c9d1d9; font-size: 14px; margin-bottom: 16px; }
        input:focus { outline: none; border-color: #58a6ff; }
        button { width: 100%; padding: 10px; border-radius: 6px; border: none; background: #238636; color: white; font-size: 14px; font-weight: 600; cursor: pointer; }
        button:hover { background: #2ea043; }
        .error { color: #f85149; font-size: 13px; margin-bottom: 12px; display: none; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>NoClaw</h1>
        <div class="subtitle">Enter password to access the control panel</div>
        <div class="error" id="error">Invalid password</div>
        <form onsubmit="login(event)">
            <label>Password</label>
            <input type="password" id="password" autofocus>
            <button type="submit">Sign In</button>
        </form>
    </div>
    <script>
        async function login(e) {
            e.preventDefault();
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error');
            errorDiv.style.display = 'none';
            try {
                const resp = await fetch('/dashboard/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password})
                });
                if (resp.ok) {
                    window.location.reload();
                } else {
                    errorDiv.style.display = 'block';
                }
            } catch (err) {
                errorDiv.textContent = 'Connection error';
                errorDiv.style.display = 'block';
            }
        }
    </script>
</body>
</html>"""

    def get_html(self) -> str:
        """Get dashboard HTML with tabbed control panel"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoClaw Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        /* Header */
        header { margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #30363d; }
        h1 { font-size: 28px; font-weight: 600; color: #58a6ff; display: inline; }
        .status-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 10px; vertical-align: middle; }
        .status-online { background: #238636; color: white; }
        .status-offline { background: #da3633; color: white; }
        .refresh-indicator { display: inline-block; width: 6px; height: 6px; background: #3fb950; border-radius: 50%; margin-right: 6px; animation: pulse 2s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .header-meta { color: #8b949e; font-size: 13px; margin-top: 6px; }

        /* Tabs */
        .tab-bar { display: flex; gap: 0; border-bottom: 1px solid #30363d; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; color: #8b949e; font-size: 14px; font-weight: 500; border-bottom: 2px solid transparent; transition: color 0.2s; }
        .tab:hover { color: #c9d1d9; }
        .tab.active { color: #f0f6fc; border-bottom-color: #58a6ff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Cards and grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 16px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }
        .card h2 { font-size: 15px; font-weight: 600; margin-bottom: 12px; color: #f0f6fc; display: flex; align-items: center; gap: 8px; }
        .stat { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; }
        .stat:last-child { border-bottom: none; }
        .stat-label { color: #8b949e; font-size: 13px; }
        .stat-value { font-weight: 600; color: #f0f6fc; font-size: 13px; }

        /* Progress bars */
        .progress-bar { width: 100%; height: 5px; background: #21262d; border-radius: 3px; overflow: hidden; margin-top: 4px; }
        .progress-fill { height: 100%; background: #58a6ff; transition: width 0.3s ease; }
        .progress-fill.warning { background: #f85149; }

        /* List items */
        .list-item { padding: 10px; margin: 4px 0; background: #0d1117; border-radius: 6px; font-size: 13px; }
        .list-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
        .list-item-meta { color: #8b949e; font-size: 12px; }
        .empty-state { text-align: center; padding: 30px; color: #8b949e; font-size: 13px; }

        /* Buttons */
        button { padding: 6px 12px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; font-size: 13px; cursor: pointer; font-weight: 500; }
        button:hover { background: #30363d; }
        button.primary { background: #238636; border-color: #238636; color: white; }
        button.primary:hover { background: #2ea043; }
        button.danger { background: #da3633; border-color: #da3633; color: white; }
        button.danger:hover { background: #f85149; }
        button.sm { padding: 3px 8px; font-size: 12px; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Toggle switch */
        .toggle { position: relative; display: inline-block; width: 36px; height: 20px; cursor: pointer; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .toggle .slider { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #21262d; border-radius: 10px; transition: 0.2s; }
        .toggle .slider:before { content: ''; position: absolute; height: 14px; width: 14px; left: 3px; bottom: 3px; background: #8b949e; border-radius: 50%; transition: 0.2s; }
        .toggle input:checked + .slider { background: #238636; }
        .toggle input:checked + .slider:before { transform: translateX(16px); background: white; }

        /* Links */
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .link-danger { color: #f85149; }

        /* Forms */
        input, textarea, select { padding: 6px 10px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #c9d1d9; font-size: 13px; font-family: inherit; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #58a6ff; }
        textarea { resize: vertical; }

        /* Task table */
        .task-table { width: 100%; border-collapse: collapse; }
        .task-table th { text-align: left; padding: 8px 12px; font-size: 12px; color: #8b949e; font-weight: 500; border-bottom: 1px solid #30363d; }
        .task-table td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #21262d; vertical-align: middle; }
        .task-table tr:hover { background: #161b22; }

        /* Editable field */
        .editable { cursor: pointer; padding: 2px 6px; border-radius: 4px; }
        .editable:hover { background: #21262d; }
        .edit-input { width: 140px; }

        /* Task history panel */
        .task-history { margin-top: 8px; padding: 10px; background: #0d1117; border-radius: 6px; border: 1px solid #21262d; }
        .task-history-item { padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 12px; }
        .task-history-item:last-child { border-bottom: none; }
        .task-response { color: #8b949e; margin-top: 4px; white-space: pre-wrap; max-height: 100px; overflow-y: auto; }

        /* Conversations layout */
        .conv-layout { display: grid; grid-template-columns: 220px 1fr; gap: 16px; min-height: 400px; }
        .conv-sidebar { background: #161b22; border: 1px solid #30363d; border-radius: 6px; overflow-y: auto; max-height: 600px; }
        .conv-sidebar-item { padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #21262d; font-size: 13px; }
        .conv-sidebar-item:hover { background: #21262d; }
        .conv-sidebar-item.active { background: #1f6feb22; border-left: 2px solid #58a6ff; }
        .conv-sidebar-count { color: #8b949e; font-size: 11px; }
        .conv-main { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; overflow-y: auto; max-height: 600px; }
        .conv-message { padding: 10px; margin: 6px 0; background: #0d1117; border-radius: 6px; }
        .conv-msg-user { color: #58a6ff; font-weight: 500; font-size: 13px; }
        .conv-msg-response { color: #c9d1d9; font-size: 13px; margin-top: 6px; white-space: pre-wrap; }
        .conv-msg-meta { color: #8b949e; font-size: 11px; margin-top: 4px; display: flex; justify-content: space-between; align-items: center; }

        /* Agent tab */
        .agent-form { display: grid; gap: 10px; margin-bottom: 16px; }
        .agent-form-row { display: flex; gap: 10px; align-items: end; }
        .agent-form label { display: block; font-size: 12px; color: #8b949e; margin-bottom: 4px; }
        .agent-result { padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; white-space: pre-wrap; font-size: 13px; max-height: 400px; overflow-y: auto; display: none; }
        .agent-result.show { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NoClaw</h1>
            <span class="status-badge status-online" id="connection-badge">
                <span class="refresh-indicator"></span>Live
            </span>
            <div class="header-meta">
                Uptime: <span id="uptime">--</span>
                <a href="#" onclick="logout();return false" style="margin-left:16px;font-size:12px;color:#8b949e">Logout</a>
            </div>
        </header>

        <!-- Tab Bar -->
        <div class="tab-bar">
            <div class="tab active" onclick="switchTab('overview')">Overview</div>
            <div class="tab" onclick="switchTab('tasks')">Tasks</div>
            <div class="tab" onclick="switchTab('conversations')">Conversations</div>
            <div class="tab" onclick="switchTab('agent')">Agent</div>
        </div>

        <!-- ==================== OVERVIEW TAB ==================== -->
        <div id="tab-overview" class="tab-content active">
            <div class="grid">
                <!-- System Stats -->
                <div class="card">
                    <h2>System</h2>
                    <div class="stat"><span class="stat-label">CPU</span><span class="stat-value" id="cpu">--%</span></div>
                    <div class="progress-bar"><div class="progress-fill" id="cpu-bar"></div></div>
                    <div class="stat"><span class="stat-label">Memory</span><span class="stat-value" id="memory">--%</span></div>
                    <div class="progress-bar"><div class="progress-fill" id="memory-bar"></div></div>
                    <div class="stat"><span class="stat-label">Disk Free</span><span class="stat-value" id="disk">-- GB</span></div>
                    <div class="stat"><span class="stat-label">Process Memory</span><span class="stat-value" id="process-mem">-- MB</span></div>
                </div>

                <!-- Channel Stats -->
                <div class="card">
                    <h2>Channels</h2>
                    <div class="stat"><span class="stat-label">Total</span><span class="stat-value" id="total-channels">--</span></div>
                    <div class="stat"><span class="stat-label">Active (24h)</span><span class="stat-value" id="active-channels">--</span></div>
                    <div class="stat"><span class="stat-label">Total Messages</span><span class="stat-value" id="total-messages">--</span></div>
                    <div class="stat"><span class="stat-label">Today</span><span class="stat-value" id="messages-today">--</span></div>
                </div>

                <!-- Heartbeat -->
                <div class="card">
                    <h2>Heartbeat
                        <span style="margin-left:auto">
                            <label class="toggle" title="Enable/Disable Heartbeat">
                                <input type="checkbox" id="heartbeat-toggle" onchange="toggleHeartbeat(this.checked)">
                                <span class="slider"></span>
                            </label>
                        </span>
                    </h2>
                    <div class="stat"><span class="stat-label">Status</span><span class="stat-value" id="heartbeat-status">--</span></div>
                    <div class="stat"><span class="stat-label">Interval</span><span class="stat-value" id="heartbeat-interval">--</span></div>
                    <div class="stat"><span class="stat-label">Tasks</span><span class="stat-value" id="heartbeat-task-count">--</span></div>
                </div>
            </div>

            <!-- Agent Sessions -->
            <div class="card" style="margin-bottom: 16px;">
                <h2>Agent Sessions <span class="stat-value" id="session-count" style="font-size: 13px; margin-left: auto;">0 active</span></h2>
                <div id="agent-sessions"><div class="empty-state">No active sessions</div></div>
            </div>

            <!-- Recent Activity -->
            <div class="grid">
                <div class="card">
                    <h2>Recent Channels</h2>
                    <div id="recent-channels"><div class="empty-state">No recent activity</div></div>
                </div>
                <div class="card">
                    <h2>Recent Task Runs</h2>
                    <div id="recent-heartbeats"><div class="empty-state">No task runs</div></div>
                </div>
            </div>
        </div>

        <!-- ==================== TASKS TAB ==================== -->
        <div id="tab-tasks" class="tab-content">
            <div class="card">
                <h2>Scheduled Tasks</h2>
                <table class="task-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Schedule</th>
                            <th>Enabled</th>
                            <th>Last Run</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="task-list"></tbody>
                </table>
                <div id="task-empty" class="empty-state" style="display:none">No tasks defined. Add .md files to workspace/.claude/tasks/</div>
            </div>

            <!-- Task run history -->
            <div class="card" style="margin-top: 16px;">
                <h2>Task Run History
                    <button class="sm" onclick="loadAllTaskHistory()" style="margin-left: auto;">Refresh</button>
                </h2>
                <div id="task-history-panel"><div class="empty-state">Select a task or click Refresh</div></div>
            </div>
        </div>

        <!-- ==================== CONVERSATIONS TAB ==================== -->
        <div id="tab-conversations" class="tab-content">
            <div class="conv-layout">
                <div class="conv-sidebar" id="conv-sidebar">
                    <div class="empty-state">Loading channels...</div>
                </div>
                <div class="conv-main" id="conv-main">
                    <div class="empty-state">Select a channel to view history</div>
                </div>
            </div>
        </div>

        <!-- ==================== AGENT TAB ==================== -->
        <div id="tab-agent" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h2>Send Message</h2>
                    <div class="agent-form">
                        <div>
                            <label>Message</label>
                            <textarea id="agent-message" rows="3" style="width:100%" placeholder="Enter your message..."></textarea>
                        </div>
                        <div class="agent-form-row">
                            <div>
                                <label>Channel</label>
                                <input type="text" id="agent-channel" value="dashboard" style="width:120px">
                            </div>
                            <div>
                                <label>Model</label>
                                <select id="agent-model" style="width:100px">
                                    <option value="">Default</option>
                                    <option value="haiku">Haiku</option>
                                    <option value="sonnet">Sonnet</option>
                                    <option value="opus">Opus</option>
                                </select>
                            </div>
                            <div>
                                <label>Resume Session</label>
                                <input type="text" id="agent-resume" placeholder="session_id" style="width:120px">
                            </div>
                            <div style="padding-bottom:1px">
                                <button class="primary" onclick="sendAgentMessage()">Send</button>
                            </div>
                        </div>
                    </div>
                    <div class="agent-result" id="agent-result"></div>
                </div>

                <div class="card">
                    <h2>Run Task</h2>
                    <div class="agent-form">
                        <div class="agent-form-row">
                            <div>
                                <label>Task</label>
                                <select id="task-runner-select" style="width:180px"></select>
                            </div>
                            <div style="padding-bottom:1px">
                                <button class="primary" onclick="runTaskFromAgent()">Run</button>
                            </div>
                        </div>
                    </div>
                    <div class="agent-result" id="task-runner-result"></div>
                </div>
            </div>

            <!-- Active Sessions -->
            <div class="card" style="margin-top: 16px;">
                <h2>Active Sessions <span class="stat-value" id="agent-session-count" style="font-size: 13px; margin-left: auto;">0</span></h2>
                <div id="agent-sessions-list"><div class="empty-state">No active sessions</div></div>
            </div>
        </div>
    </div>

<script>
// ==================== STATE ====================
let currentTab = 'overview';
let latestData = {};
let selectedChannel = null;

// ==================== SSE ====================
const eventSource = new EventSource('/dashboard/stream');
eventSource.onmessage = function(event) {
    latestData = JSON.parse(event.data);
    updateOverview(latestData);
    updateTasksFromSSE(latestData);
    updateAgentTab(latestData);
};
eventSource.onerror = function() {
    document.getElementById('connection-badge').className = 'status-badge status-offline';
    document.getElementById('connection-badge').innerHTML = 'Disconnected';
};

// ==================== TAB SWITCHING ====================
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', ['overview','tasks','conversations','agent'][i] === tab);
    });
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');

    if (tab === 'conversations' && !selectedChannel) loadChannelList();
    if (tab === 'tasks') updateTasksFromSSE(latestData);
}

// ==================== OVERVIEW ====================
function updateOverview(data) {
    if (data.system) {
        const s = data.system;
        setText('cpu', (s.cpu_percent?.toFixed(1) || '--') + '%');
        setText('memory', (s.memory_percent?.toFixed(1) || '--') + '%');
        setText('disk', (s.disk_free_gb?.toFixed(1) || '--') + ' GB');
        setText('process-mem', (s.process_memory_mb?.toFixed(0) || '--') + ' MB');

        setBar('cpu-bar', s.cpu_percent || 0);
        setBar('memory-bar', s.memory_percent || 0);

        if (s.uptime_seconds) {
            const h = Math.floor(s.uptime_seconds / 3600);
            const m = Math.floor((s.uptime_seconds % 3600) / 60);
            setText('uptime', h > 0 ? h + 'h ' + m + 'm' : m + 'm');
        }
    }

    if (data.channels) {
        const c = data.channels;
        setText('total-channels', c.total_channels || 0);
        setText('active-channels', c.active_channels_24h || 0);
        setText('total-messages', c.total_messages || 0);
        setText('messages-today', c.messages_today || 0);

        const recentDiv = document.getElementById('recent-channels');
        if (c.recent_channels?.length > 0) {
            recentDiv.innerHTML = c.recent_channels.map(ch =>
                '<div class="list-item"><div class="list-item-header">' +
                '<strong>' + esc(ch.channel) + '</strong>' +
                '<span class="list-item-meta">' + formatTime(ch.last_active) + '</span>' +
                '</div></div>'
            ).join('');
        } else {
            recentDiv.innerHTML = '<div class="empty-state">No recent activity</div>';
        }
    }

    if (data.sessions) {
        setText('session-count', (data.sessions.active || 0) + ' active');
        const sessDiv = document.getElementById('agent-sessions');
        if (data.sessions.sessions?.length > 0) {
            sessDiv.innerHTML = data.sessions.sessions.map(s =>
                '<div class="list-item"><div class="list-item-header">' +
                '<strong>' + esc(s.name) + '</strong>' +
                '<span class="list-item-meta">' + (s.model || '') + ' &middot; ' + Math.round(s.elapsed_seconds || 0) + 's</span>' +
                '</div><div class="list-item-meta">' +
                esc(s.prompt_preview || '') +
                ' &middot; <a href="/sessions/' + esc(s.name) + '/logs" target="_blank">logs</a>' +
                ' &middot; <a href="#" class="link-danger" onclick="killSession(\\'' + esc(s.name) + '\\');return false">kill</a>' +
                '</div></div>'
            ).join('');
        } else {
            sessDiv.innerHTML = '<div class="empty-state">No active sessions</div>';
        }
    }

    if (data.heartbeat) {
        const hb = data.heartbeat;
        const toggle = document.getElementById('heartbeat-toggle');
        if (toggle && document.activeElement !== toggle) toggle.checked = hb.enabled;
        setText('heartbeat-status', data.scheduler_running ? 'Running' : 'Stopped');
        setText('heartbeat-interval', formatInterval(hb.interval || 1800));
        setText('heartbeat-task-count', (hb.tasks?.length || 0) + ' defined');

        const recentHBDiv = document.getElementById('recent-heartbeats');
        if (hb.recent_logs?.length > 0) {
            recentHBDiv.innerHTML = hb.recent_logs.map(log =>
                '<div class="list-item"><div class="list-item-header">' +
                '<strong>' + esc(log.task_name || 'task') + '</strong>' +
                '<span class="list-item-meta">' + formatTime(log.timestamp) + '</span>' +
                '</div><div class="list-item-meta">' + esc(log.result) + '</div></div>'
            ).join('');
        } else {
            recentHBDiv.innerHTML = '<div class="empty-state">No task runs</div>';
        }
    }
}

// ==================== TASKS ====================
function updateTasksFromSSE(data) {
    if (!data.heartbeat?.tasks) return;
    const tasks = data.heartbeat.tasks;
    const tbody = document.getElementById('task-list');
    const emptyDiv = document.getElementById('task-empty');

    if (tasks.length === 0) {
        tbody.innerHTML = '';
        emptyDiv.style.display = 'block';
        return;
    }
    emptyDiv.style.display = 'none';

    // Also update the task runner dropdown
    const sel = document.getElementById('task-runner-select');
    if (sel && sel.options.length !== tasks.length) {
        sel.innerHTML = tasks.map(t => '<option value="' + esc(t.name) + '">' + esc(t.name) + '</option>').join('');
    }

    tbody.innerHTML = tasks.map(t =>
        '<tr>' +
        '<td><strong>' + esc(t.name) + '</strong></td>' +
        '<td><span class="editable" onclick="editSchedule(this, \\'' + esc(t.name) + '\\')">' + esc(t.schedule || 'on-demand') + '</span></td>' +
        '<td><label class="toggle"><input type="checkbox" ' + (t.enabled ? 'checked' : '') +
            ' onchange="toggleTask(\\'' + esc(t.name) + '\\', this.checked)"><span class="slider"></span></label></td>' +
        '<td class="list-item-meta">' + (t.last_run ? formatTime(t.last_run) : 'Never') + '</td>' +
        '<td>' +
            '<button class="sm" onclick="runTask(\\'' + esc(t.name) + '\\', this)">Run Now</button> ' +
            '<button class="sm" onclick="showTaskHistory(\\'' + esc(t.name) + '\\')">History</button>' +
        '</td>' +
        '</tr>'
    ).join('');
}

async function toggleTask(name, enabled) {
    try {
        await apiFetch('/tasks/' + name, {method: 'PATCH', body: JSON.stringify({enabled})});
    } catch (e) { showError('Failed to update task: ' + e.message); }
}

function editSchedule(el, name) {
    const current = el.textContent;
    const input = document.createElement('input');
    input.className = 'edit-input';
    input.value = current === 'on-demand' ? '' : current;
    input.placeholder = 'e.g. every morning';

    async function save() {
        const newVal = input.value.trim();
        try {
            await apiFetch('/tasks/' + name, {method: 'PATCH', body: JSON.stringify({schedule: newVal})});
        } catch (e) { showError('Failed to update schedule: ' + e.message); }
        // SSE will refresh the display
    }

    input.onblur = save;
    input.onkeydown = function(e) { if (e.key === 'Enter') { input.blur(); } if (e.key === 'Escape') { input.onblur = null; el.textContent = current; el.style.display = ''; input.remove(); } };
    el.style.display = 'none';
    el.parentNode.insertBefore(input, el.nextSibling);
    input.focus();
    input.select();
}

async function runTask(name, btn) {
    if (btn) { btn.disabled = true; btn.textContent = 'Running...'; }
    try {
        const data = await apiFetch('/tasks/' + name + '/run', {method: 'POST'});
        if (btn) { btn.textContent = 'Done'; setTimeout(() => { btn.textContent = 'Run Now'; btn.disabled = false; }, 2000); }
    } catch (e) {
        showError('Task failed: ' + e.message);
        if (btn) { btn.textContent = 'Failed'; setTimeout(() => { btn.textContent = 'Run Now'; btn.disabled = false; }, 2000); }
    }
}

async function showTaskHistory(name) {
    const panel = document.getElementById('task-history-panel');
    panel.innerHTML = '<div class="empty-state">Loading...</div>';
    try {
        const data = await apiFetch('/tasks/' + name + '/history');
        if (!data.history?.length) {
            panel.innerHTML = '<div class="empty-state">No run history for ' + esc(name) + '</div>';
            return;
        }
        panel.innerHTML = '<h3 style="font-size:14px;margin-bottom:8px;color:#f0f6fc">' + esc(name) + '</h3>' +
            data.history.map(h =>
                '<div class="task-history-item"><div class="list-item-header">' +
                '<span>' + formatTime(h.timestamp) + '</span>' +
                '<button class="sm danger" onclick="deleteTaskRun(' + h.id + ', this)">Delete</button>' +
                '</div>' +
                '<div class="task-response">' + esc(h.response || 'No response') + '</div></div>'
            ).join('');
    } catch (e) { panel.innerHTML = '<div class="empty-state">Error: ' + esc(e.message) + '</div>'; }
}

async function loadAllTaskHistory() {
    const panel = document.getElementById('task-history-panel');
    panel.innerHTML = '<div class="empty-state">Loading...</div>';
    try {
        // Use the heartbeat recent_logs from SSE data
        const data = latestData.heartbeat;
        if (!data?.recent_logs?.length) {
            panel.innerHTML = '<div class="empty-state">No recent task runs</div>';
            return;
        }
        panel.innerHTML = data.recent_logs.map(h =>
            '<div class="task-history-item"><div class="list-item-header">' +
            '<strong>' + esc(h.task_name || 'task') + '</strong>' +
            '<span>' + formatTime(h.timestamp) + ' ' +
            '<button class="sm danger" onclick="deleteTaskRun(' + h.id + ', this)">Delete</button></span>' +
            '</div>' +
            '<div class="task-response">' + esc(h.result || 'No response') + '</div></div>'
        ).join('');
    } catch (e) { panel.innerHTML = '<div class="empty-state">Error loading history</div>'; }
}

async function deleteTaskRun(id, btn) {
    if (!confirm('Delete this task run?')) return;
    try {
        await apiFetch('/history/heartbeat/' + id, {method: 'DELETE'});
        if (btn) btn.closest('.task-history-item').remove();
    } catch (e) { showError('Delete failed: ' + e.message); }
}

// ==================== CONVERSATIONS ====================
async function loadChannelList() {
    const sidebar = document.getElementById('conv-sidebar');
    try {
        const data = await apiFetch('/channels');
        if (!data.channels?.length) {
            sidebar.innerHTML = '<div class="empty-state">No channels</div>';
            return;
        }
        sidebar.innerHTML = data.channels.map(ch =>
            '<div class="conv-sidebar-item" onclick="selectChannel(\\'' + esc(ch.channel) + '\\', this)">' +
            '<div>' + esc(ch.channel) + '</div>' +
            '<div class="conv-sidebar-count">' + ch.message_count + ' messages &middot; ' + formatTime(ch.last_active) + '</div>' +
            '</div>'
        ).join('');
    } catch (e) { sidebar.innerHTML = '<div class="empty-state">Error loading channels</div>'; }
}

async function selectChannel(channel, el) {
    selectedChannel = channel;
    document.querySelectorAll('.conv-sidebar-item').forEach(i => i.classList.remove('active'));
    if (el) el.classList.add('active');

    const main = document.getElementById('conv-main');
    main.innerHTML = '<div class="empty-state">Loading...</div>';
    try {
        const data = await apiFetch('/history/' + encodeURIComponent(channel) + '?limit=50');
        const messages = (data.history || []).reverse(); // oldest first
        if (!messages.length) {
            main.innerHTML = '<div class="empty-state">No messages in this channel</div>' +
                '<div style="text-align:center;margin-top:10px"><button class="sm danger" onclick="clearChannelHistory(\\'' + esc(channel) + '\\')">Clear Channel</button></div>';
            return;
        }
        main.innerHTML =
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">' +
            '<strong>' + esc(channel) + '</strong>' +
            '<button class="sm danger" onclick="clearChannelHistory(\\'' + esc(channel) + '\\')">Clear All</button></div>' +
            messages.map(m =>
                '<div class="conv-message" id="msg-' + m.id + '">' +
                '<div class="conv-msg-user">User: ' + esc(m.message) + '</div>' +
                (m.response ? '<div class="conv-msg-response">' + esc(m.response) + '</div>' : '') +
                '<div class="conv-msg-meta"><span>' +
                formatTime(m.timestamp) +
                (m.model_used ? ' &middot; ' + esc(m.model_used) : '') +
                (m.tokens_used ? ' &middot; ' + m.tokens_used + ' tokens' : '') +
                '</span><button class="sm" onclick="deleteMessage(\\'' + esc(channel) + '\\', ' + m.id + ')">Delete</button></div></div>'
            ).join('');
    } catch (e) { main.innerHTML = '<div class="empty-state">Error: ' + esc(e.message) + '</div>'; }
}

async function deleteMessage(channel, id) {
    try {
        await apiFetch('/history/' + encodeURIComponent(channel) + '/' + id, {method: 'DELETE'});
        const el = document.getElementById('msg-' + id);
        if (el) el.remove();
    } catch (e) { showError('Delete failed: ' + e.message); }
}

async function clearChannelHistory(channel) {
    if (!confirm('Delete all messages in ' + channel + '?')) return;
    try {
        await apiFetch('/history/' + encodeURIComponent(channel), {method: 'DELETE'});
        selectChannel(channel);
        loadChannelList();
    } catch (e) { showError('Clear failed: ' + e.message); }
}

// ==================== AGENT ====================
function updateAgentTab(data) {
    if (data.sessions) {
        setText('agent-session-count', data.sessions.active || 0);
        const div = document.getElementById('agent-sessions-list');
        if (data.sessions.sessions?.length > 0) {
            div.innerHTML = data.sessions.sessions.map(s =>
                '<div class="list-item"><div class="list-item-header">' +
                '<strong>' + esc(s.name) + '</strong>' +
                '<span class="list-item-meta">' + (s.model || '') + ' &middot; ' + Math.round(s.elapsed_seconds || 0) + 's ' +
                '<a href="#" class="link-danger" onclick="killSession(\\'' + esc(s.name) + '\\');return false">kill</a></span>' +
                '</div></div>'
            ).join('');
        } else {
            div.innerHTML = '<div class="empty-state">No active sessions</div>';
        }
    }
}

async function sendAgentMessage() {
    const message = document.getElementById('agent-message').value;
    if (!message.trim()) return;
    const channel = document.getElementById('agent-channel').value || 'dashboard';
    const model = document.getElementById('agent-model').value;
    const resume = document.getElementById('agent-resume').value;

    const resultDiv = document.getElementById('agent-result');
    resultDiv.textContent = 'Sending...';
    resultDiv.classList.add('show');

    try {
        const body = {message, channel};
        if (model) body.model_hint = model;
        if (resume) body.resume = resume;

        const data = await apiFetch('/webhook', {method: 'POST', body: JSON.stringify(body)});
        resultDiv.textContent = data.response || data.error || JSON.stringify(data);
        if (data.session_id) {
            document.getElementById('agent-resume').value = data.session_id;
        }
    } catch (e) { resultDiv.textContent = 'Error: ' + e.message; }
}

async function runTaskFromAgent() {
    const name = document.getElementById('task-runner-select').value;
    if (!name) return;
    const resultDiv = document.getElementById('task-runner-result');
    resultDiv.textContent = 'Running ' + name + '...';
    resultDiv.classList.add('show');
    try {
        const data = await apiFetch('/tasks/' + name + '/run', {method: 'POST'});
        resultDiv.textContent = data.response || 'Task completed';
    } catch (e) { resultDiv.textContent = 'Error: ' + e.message; }
}

// ==================== HEARTBEAT TOGGLE ====================
async function toggleHeartbeat(enabled) {
    try {
        if (enabled) {
            await apiFetch('/heartbeat/enable', {method: 'POST'});
        } else {
            await apiFetch('/heartbeat/disable', {method: 'POST'});
        }
    } catch (e) { showError('Failed to toggle heartbeat: ' + e.message); }
}

// ==================== SHARED ====================
async function killSession(name) {
    if (!confirm('Kill session ' + name + '?')) return;
    try {
        const data = await apiFetch('/sessions/' + name + '/kill', {method: 'POST'});
        if (data.status !== 'killed') showError('Unexpected: ' + JSON.stringify(data));
    } catch (e) { showError('Error: ' + e.message); }
}

async function apiFetch(url, opts = {}) {
    const headers = {'Content-Type': 'application/json'};
    const apiKey = localStorage.getItem('noclaw_api_key');
    if (apiKey) headers['X-API-Key'] = apiKey;
    const resp = await fetch(url, {...opts, headers});
    if (resp.status === 401) {
        const key = prompt('API Key required:');
        if (key) {
            localStorage.setItem('noclaw_api_key', key);
            return apiFetch(url, opts); // retry
        }
        throw new Error('Authentication required');
    }
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || resp.statusText);
    }
    return resp.json();
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setBar(id, pct) {
    const el = document.getElementById(id);
    if (el) {
        el.style.width = pct + '%';
        el.className = 'progress-fill' + (pct > 80 ? ' warning' : '');
    }
}

function esc(s) {
    if (s == null) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
}

function formatTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000 / 60);
    if (diff < 1) return 'Just now';
    if (diff < 60) return diff + 'm ago';
    if (diff < 1440) return Math.floor(diff / 60) + 'h ago';
    return Math.floor(diff / 1440) + 'd ago';
}

function formatInterval(seconds) {
    if (seconds >= 3600) return (seconds / 3600) + 'h';
    return (seconds / 60) + 'm';
}

async function logout() {
    await fetch('/dashboard/logout', {method: 'POST'});
    window.location.reload();
}

function showError(msg) {
    alert(msg);
}
</script>
</body>
</html>"""


async def stream_events(dashboard):
    """Generate Server-Sent Events stream"""
    while True:
        try:
            data = dashboard.get_dashboard_data()
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error streaming events: {e}")
            await asyncio.sleep(5)
