#!/usr/bin/env python3
"""
Simple Monitoring Dashboard

Lightweight HTML dashboard with Server-Sent Events for real-time updates.
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
    """Simple monitoring dashboard for NoClaw"""

    def __init__(self, assistant):
        """
        Initialize dashboard

        Args:
            assistant: Reference to PersonalAssistant
        """
        self.assistant = assistant
        logger.info("Dashboard initialized")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Process info
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Calculate uptime (process.create_time() returns Unix timestamp)
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

                # Total channels
                cursor.execute("SELECT COUNT(*) FROM channels")
                total_channels = cursor.fetchone()[0]

                # Active channels (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) FROM channels
                    WHERE datetime(last_active) > datetime('now', '-1 day')
                """)
                active_channels = cursor.fetchone()[0]

                # Recent channels (last hour)
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

                # Total messages
                cursor.execute("SELECT COUNT(*) FROM message_history")
                total_messages = cursor.fetchone()[0]

                # Messages today
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

                # Recent heartbeat activity from message_history
                cursor.execute("""
                    SELECT timestamp, response
                    FROM message_history
                    WHERE channel = 'heartbeat'
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                recent_logs = [
                    {
                        "timestamp": row[0],
                        "result": row[1][:100] if row[1] else "N/A"
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

    def get_html(self) -> str:
        """Get dashboard HTML"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoClaw Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        header { margin-bottom: 30px; border-bottom: 1px solid #30363d; padding-bottom: 20px; }
        h1 { font-size: 32px; font-weight: 600; color: #58a6ff; }
        .subtitle { color: #8b949e; margin-top: 5px; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 10px; }
        .status-online { background: #1f6feb; color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; }
        .card h2 { font-size: 16px; font-weight: 600; margin-bottom: 15px; color: #f0f6fc; display: flex; align-items: center; gap: 8px; }
        .stat { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #21262d; }
        .stat:last-child { border-bottom: none; }
        .stat-label { color: #8b949e; }
        .stat-value { font-weight: 600; color: #f0f6fc; }
        .list-item { padding: 10px; margin: 5px 0; background: #0d1117; border-radius: 6px; font-size: 13px; }
        .list-item-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
        .list-item-meta { color: #8b949e; font-size: 12px; }
        .progress-bar { width: 100%; height: 6px; background: #21262d; border-radius: 3px; overflow: hidden; margin-top: 5px; }
        .progress-fill { height: 100%; background: #58a6ff; transition: width 0.3s ease; }
        .progress-fill.warning { background: #f85149; }
        .empty-state { text-align: center; padding: 40px; color: #8b949e; }
        .refresh-indicator { display: inline-block; width: 8px; height: 8px; background: #3fb950; border-radius: 50%; margin-right: 8px; animation: pulse 2s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .test-section { margin-top: 20px; padding: 20px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; }
        .test-form { display: flex; gap: 10px; margin-top: 10px; }
        input, button { padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #c9d1d9; font-size: 14px; }
        input { flex: 1; }
        button { background: #1f6feb; border-color: #1f6feb; color: white; cursor: pointer; font-weight: 600; }
        button:hover { background: #1a5cd7; }
        .test-result { margin-top: 10px; padding: 10px; border-radius: 6px; background: #0d1117; display: none; }
        .test-result.show { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>
                NoClaw Dashboard
                <span class="status-badge status-online">
                    <span class="refresh-indicator"></span>
                    Live
                </span>
            </h1>
            <div class="subtitle">Real-time monitoring &bull; Updated every 5 seconds</div>
        </header>

        <div class="grid">
            <!-- System Stats -->
            <div class="card">
                <h2>System Status</h2>
                <div class="stat"><span class="stat-label">CPU Usage</span><span class="stat-value" id="cpu">--%</span></div>
                <div class="progress-bar"><div class="progress-fill" id="cpu-bar"></div></div>
                <div class="stat"><span class="stat-label">Memory Usage</span><span class="stat-value" id="memory">--%</span></div>
                <div class="progress-bar"><div class="progress-fill" id="memory-bar"></div></div>
                <div class="stat"><span class="stat-label">Disk Free</span><span class="stat-value" id="disk">-- GB</span></div>
                <div class="stat"><span class="stat-label">Process Memory</span><span class="stat-value" id="process-mem">-- MB</span></div>
            </div>

            <!-- Channel Stats -->
            <div class="card">
                <h2>Channels</h2>
                <div class="stat"><span class="stat-label">Total Channels</span><span class="stat-value" id="total-channels">--</span></div>
                <div class="stat"><span class="stat-label">Active (24h)</span><span class="stat-value" id="active-channels">--</span></div>
                <div class="stat"><span class="stat-label">Total Messages</span><span class="stat-value" id="total-messages">--</span></div>
                <div class="stat"><span class="stat-label">Messages Today</span><span class="stat-value" id="messages-today">--</span></div>
            </div>

            <!-- Heartbeat Stats -->
            <div class="card">
                <h2>Heartbeat</h2>
                <div class="stat"><span class="stat-label">Enabled</span><span class="stat-value" id="heartbeat-enabled">--</span></div>
                <div class="stat"><span class="stat-label">Status</span><span class="stat-value" id="heartbeat-status">--</span></div>
                <div class="stat"><span class="stat-label">Interval</span><span class="stat-value" id="heartbeat-interval">--</span></div>
                <div id="heartbeat-tasks"></div>
            </div>
        </div>

        <!-- Agent Sessions -->
        <div class="card" style="margin-bottom: 20px;">
            <h2>Agent Sessions <span class="stat-value" id="session-count" style="font-size: 14px; margin-left: auto;">0 active</span></h2>
            <div id="agent-sessions"><div class="empty-state">No active agent sessions</div></div>
        </div>

        <!-- Recent Activity -->
        <div class="card">
            <h2>Recent Channels (Last Hour)</h2>
            <div id="recent-channels"><div class="empty-state">No recent activity</div></div>
        </div>

        <!-- Recent Heartbeats -->
        <div class="card">
            <h2>Recent Task Runs</h2>
            <div id="recent-heartbeats"><div class="empty-state">No heartbeat activity</div></div>
        </div>

        <!-- Quick Test -->
        <div class="test-section">
            <h2>Quick Test Message</h2>
            <div class="test-form">
                <input type="text" id="test-message" placeholder="Message" value="Hello!">
                <button onclick="sendTest()">Send Test</button>
            </div>
            <div class="test-result" id="test-result"></div>
        </div>
    </div>

    <script>
        const eventSource = new EventSource('/dashboard/stream');
        eventSource.onmessage = function(event) { updateDashboard(JSON.parse(event.data)); };
        eventSource.onerror = function() { console.error('SSE connection error'); };

        function updateDashboard(data) {
            if (data.system) {
                document.getElementById('cpu').textContent = data.system.cpu_percent?.toFixed(1) + '%' || '--%';
                document.getElementById('memory').textContent = data.system.memory_percent?.toFixed(1) + '%' || '--%';
                document.getElementById('disk').textContent = data.system.disk_free_gb?.toFixed(1) + ' GB' || '-- GB';
                document.getElementById('process-mem').textContent = data.system.process_memory_mb?.toFixed(0) + ' MB' || '-- MB';
                const cpuBar = document.getElementById('cpu-bar');
                cpuBar.style.width = (data.system.cpu_percent || 0) + '%';
                cpuBar.className = 'progress-fill' + (data.system.cpu_percent > 80 ? ' warning' : '');
                const memBar = document.getElementById('memory-bar');
                memBar.style.width = (data.system.memory_percent || 0) + '%';
                memBar.className = 'progress-fill' + (data.system.memory_percent > 80 ? ' warning' : '');
            }

            if (data.channels) {
                document.getElementById('total-channels').textContent = data.channels.total_channels || 0;
                document.getElementById('active-channels').textContent = data.channels.active_channels_24h || 0;
                document.getElementById('total-messages').textContent = data.channels.total_messages || 0;
                document.getElementById('messages-today').textContent = data.channels.messages_today || 0;

                const recentDiv = document.getElementById('recent-channels');
                if (data.channels.recent_channels && data.channels.recent_channels.length > 0) {
                    recentDiv.innerHTML = data.channels.recent_channels.map(ch => `
                        <div class="list-item">
                            <div class="list-item-header">
                                <strong>${ch.channel}</strong>
                                <span class="list-item-meta">${formatTime(ch.last_active)}</span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    recentDiv.innerHTML = '<div class="empty-state">No recent activity</div>';
                }
            }

            if (data.sessions) {
                document.getElementById('session-count').textContent = (data.sessions.active || 0) + ' active';
                const sessDiv = document.getElementById('agent-sessions');
                if (data.sessions.sessions && data.sessions.sessions.length > 0) {
                    sessDiv.innerHTML = data.sessions.sessions.map(s => `
                        <div class="list-item">
                            <div class="list-item-header">
                                <strong>${s.name}</strong>
                                <span class="list-item-meta">${s.model || ''}</span>
                            </div>
                            <div class="list-item-meta">
                                ${s.prompt_preview || ''}
                                &middot; <a href="/sessions/${s.name}/logs" target="_blank" style="color:#58a6ff">view logs</a>
                                &middot; <a href="#" onclick="killSession('${s.name}');return false" style="color:#f85149">kill</a>
                            </div>
                        </div>
                    `).join('');
                } else {
                    sessDiv.innerHTML = '<div class="empty-state">No active agent sessions</div>';
                }
            }

            if (data.heartbeat) {
                document.getElementById('heartbeat-enabled').textContent = data.heartbeat.enabled ? 'Yes' : 'No';
                document.getElementById('heartbeat-status').textContent = data.scheduler_running ? 'Running' : 'Stopped';
                document.getElementById('heartbeat-interval').textContent = (data.heartbeat.interval || 1800) + 's';

                const tasksDiv = document.getElementById('heartbeat-tasks');
                if (data.heartbeat.tasks && data.heartbeat.tasks.length > 0) {
                    tasksDiv.innerHTML = data.heartbeat.tasks.map(t => `
                        <div class="list-item">
                            <div class="list-item-header">
                                <strong>${t.name}</strong>
                                <span class="list-item-meta">${t.enabled ? t.schedule : 'disabled'}</span>
                            </div>
                            ${t.last_run ? '<div class="list-item-meta">Last: ' + formatTime(t.last_run) + '</div>' : ''}
                        </div>
                    `).join('');
                }

                const recentHBDiv = document.getElementById('recent-heartbeats');
                if (data.heartbeat.recent_logs && data.heartbeat.recent_logs.length > 0) {
                    recentHBDiv.innerHTML = data.heartbeat.recent_logs.map(log => `
                        <div class="list-item">
                            <div class="list-item-header">
                                <span class="list-item-meta">${formatTime(log.timestamp)}</span>
                            </div>
                            <div class="list-item-meta">${log.result}</div>
                        </div>
                    `).join('');
                } else {
                    recentHBDiv.innerHTML = '<div class="empty-state">No heartbeat activity</div>';
                }
            }
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

        async function killSession(name) {
            if (!confirm('Kill session ' + name + '?')) return;
            try {
                const resp = await fetch('/sessions/' + name + '/kill', {method: 'POST'});
                const data = await resp.json();
                alert(data.status === 'killed' ? 'Session killed' : 'Error: ' + JSON.stringify(data));
            } catch (e) { alert('Error: ' + e.message); }
        }

        async function sendTest() {
            const message = document.getElementById('test-message').value;
            const resultDiv = document.getElementById('test-result');
            resultDiv.textContent = 'Sending...';
            resultDiv.classList.add('show');
            try {
                const response = await fetch('/dashboard/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message})
                });
                const data = await response.json();
                resultDiv.textContent = 'Response: ' + data.response;
            } catch (error) { resultDiv.textContent = 'Error: ' + error.message; }
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
            await asyncio.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Error streaming events: {e}")
            await asyncio.sleep(5)
