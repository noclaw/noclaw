#!/usr/bin/env python3
"""
NoClaw Status Dashboard

Minimal status page with system stats and test message form.
Full control panel available at /ui (React web UI).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import psutil
import os

logger = logging.getLogger(__name__)


class Dashboard:
    """NoClaw status dashboard"""

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
        """Get minimal status dashboard with test message form"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoClaw Status</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        header { margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #30363d; }
        h1 { font-size: 28px; font-weight: 600; color: #58a6ff; display: inline; }
        .status-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 10px; vertical-align: middle; }
        .status-online { background: #238636; color: white; }
        .status-offline { background: #da3633; color: white; }
        .pulse { display: inline-block; width: 6px; height: 6px; background: #3fb950; border-radius: 50%; margin-right: 6px; animation: pulse 2s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .meta { color: #8b949e; font-size: 13px; margin-top: 6px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
        .card h3 { font-size: 11px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
        .stat { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; }
        .stat-label { color: #8b949e; }
        .stat-value { color: #c9d1d9; font-weight: 500; }
        .bar-track { height: 4px; background: #21262d; border-radius: 2px; margin-top: 4px; margin-bottom: 8px; }
        .bar-fill { height: 100%; border-radius: 2px; background: #58a6ff; transition: width 0.5s; }
        .bar-fill.warn { background: #d29922; }
        .send-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
        .send-card h3 { font-size: 11px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
        textarea { width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #c9d1d9; font-family: inherit; font-size: 14px; resize: vertical; }
        textarea:focus { outline: none; border-color: #58a6ff; }
        .send-row { display: flex; gap: 10px; margin-top: 10px; align-items: center; }
        select { padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #c9d1d9; font-size: 14px; }
        select:focus { outline: none; border-color: #58a6ff; }
        .btn { padding: 8px 20px; border-radius: 6px; border: none; background: #238636; color: white; font-size: 14px; font-weight: 600; cursor: pointer; }
        .btn:hover { background: #2ea043; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .result { margin-top: 12px; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; font-size: 13px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; display: none; }
        .ui-link { float: right; font-size: 13px; color: #58a6ff; text-decoration: none; }
        .ui-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>NoClaw</h1>
            <span class="status-badge status-online" id="connection-badge"><span class="pulse"></span> Live</span>
            <a href="/ui" class="ui-link">Open Control Panel &rarr;</a>
            <div class="meta" id="header-meta"></div>
        </header>

        <div class="grid" id="status-grid">
            <!-- System -->
            <div class="card">
                <h3>System</h3>
                <div class="stat"><span class="stat-label">CPU</span><span class="stat-value" id="cpu">-</span></div>
                <div class="bar-track"><div class="bar-fill" id="cpu-bar" style="width:0"></div></div>
                <div class="stat"><span class="stat-label">Memory</span><span class="stat-value" id="mem">-</span></div>
                <div class="bar-track"><div class="bar-fill" id="mem-bar" style="width:0"></div></div>
                <div class="stat"><span class="stat-label">Disk Free</span><span class="stat-value" id="disk">-</span></div>
                <div class="stat"><span class="stat-label">Process</span><span class="stat-value" id="proc">-</span></div>
                <div class="stat"><span class="stat-label">Uptime</span><span class="stat-value" id="uptime">-</span></div>
            </div>
            <!-- Channels -->
            <div class="card">
                <h3>Channels</h3>
                <div class="stat"><span class="stat-label">Total</span><span class="stat-value" id="ch-total">-</span></div>
                <div class="stat"><span class="stat-label">Active (24h)</span><span class="stat-value" id="ch-active">-</span></div>
                <div class="stat"><span class="stat-label">Total Messages</span><span class="stat-value" id="ch-msgs">-</span></div>
                <div class="stat"><span class="stat-label">Today</span><span class="stat-value" id="ch-today">-</span></div>
            </div>
            <!-- Heartbeat -->
            <div class="card">
                <h3>Heartbeat</h3>
                <div class="stat"><span class="stat-label">Status</span><span class="stat-value" id="hb-status">-</span></div>
                <div class="stat"><span class="stat-label">Interval</span><span class="stat-value" id="hb-interval">-</span></div>
                <div class="stat"><span class="stat-label">Tasks</span><span class="stat-value" id="hb-tasks">-</span></div>
                <div class="stat"><span class="stat-label">Enabled</span><span class="stat-value" id="hb-enabled">-</span></div>
            </div>
        </div>

        <!-- Send Test Message -->
        <div class="send-card">
            <h3>Send Test Message</h3>
            <textarea id="message" rows="3" placeholder="Enter a message..."></textarea>
            <div class="send-row">
                <select id="model">
                    <option value="">Default</option>
                    <option value="haiku">Haiku</option>
                    <option value="sonnet">Sonnet</option>
                    <option value="opus">Opus</option>
                </select>
                <button class="btn" id="send-btn" onclick="sendMessage()">Send</button>
            </div>
            <div class="result" id="result"></div>
        </div>
    </div>

    <script>
        function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

        function formatUptime(s) {
            const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
            return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
        }

        function setBar(id, pct) {
            const el = document.getElementById(id);
            el.style.width = Math.min(pct, 100) + '%';
            el.className = 'bar-fill' + (pct > 80 ? ' warn' : '');
        }

        function update(data) {
            const s = data.system;
            document.getElementById('cpu').textContent = s.cpu_percent.toFixed(1) + '%';
            setBar('cpu-bar', s.cpu_percent);
            document.getElementById('mem').textContent = s.memory_percent.toFixed(1) + '%';
            setBar('mem-bar', s.memory_percent);
            document.getElementById('disk').textContent = s.disk_free_gb.toFixed(1) + ' GB';
            document.getElementById('proc').textContent = s.process_memory_mb.toFixed(0) + ' MB';
            document.getElementById('uptime').textContent = formatUptime(s.uptime_seconds);

            const c = data.channels;
            document.getElementById('ch-total').textContent = c.total_channels;
            document.getElementById('ch-active').textContent = c.active_channels_24h;
            document.getElementById('ch-msgs').textContent = c.total_messages;
            document.getElementById('ch-today').textContent = c.messages_today;

            const hb = data.heartbeat;
            document.getElementById('hb-status').textContent = data.scheduler_running ? 'Running' : 'Stopped';
            document.getElementById('hb-status').style.color = data.scheduler_running ? '#3fb950' : '#8b949e';
            document.getElementById('hb-interval').textContent = hb.interval + 's';
            document.getElementById('hb-tasks').textContent = hb.tasks.length;
            document.getElementById('hb-enabled').textContent = hb.tasks.filter(t => t.enabled).length;

            document.getElementById('header-meta').textContent =
                data.sessions.active + ' active session' + (data.sessions.active !== 1 ? 's' : '') +
                ' · ' + c.messages_today + ' messages today';
        }

        // Initial fetch + SSE
        fetch('/dashboard/data').then(r => r.json()).then(update);

        const sse = new EventSource('/dashboard/stream');
        sse.onmessage = function(e) { update(JSON.parse(e.data)); };
        sse.onerror = function() {
            const b = document.getElementById('connection-badge');
            b.className = 'status-badge status-offline';
            b.innerHTML = 'Disconnected';
        };

        // Send test message
        async function sendMessage() {
            const msg = document.getElementById('message').value.trim();
            if (!msg) return;
            const btn = document.getElementById('send-btn');
            const resultDiv = document.getElementById('result');
            btn.disabled = true;
            btn.textContent = 'Sending...';
            resultDiv.style.display = 'none';

            const body = { message: msg, channel: 'dashboard' };
            const model = document.getElementById('model').value;
            if (model) body.model_hint = model;

            try {
                const headers = { 'Content-Type': 'application/json' };
                const apiKey = localStorage.getItem('noclaw_api_key');
                if (apiKey) headers['X-API-Key'] = apiKey;

                const resp = await fetch('/webhook', { method: 'POST', headers, body: JSON.stringify(body) });
                if (resp.status === 401) {
                    const key = prompt('API Key required:');
                    if (key) { localStorage.setItem('noclaw_api_key', key); return sendMessage(); }
                }
                const data = await resp.json();
                resultDiv.textContent = data.response || data.detail || JSON.stringify(data);
            } catch (err) {
                resultDiv.textContent = 'Error: ' + err.message;
            }
            resultDiv.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Send';
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
