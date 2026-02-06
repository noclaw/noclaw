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

    def get_user_stats(self) -> Dict[str, Any]:
        """Get user activity statistics"""
        try:
            import sqlite3

            with sqlite3.connect(self.assistant.db_path) as conn:
                cursor = conn.cursor()

                # Total users
                cursor.execute("SELECT COUNT(*) FROM contexts")
                total_users = cursor.fetchone()[0]

                # Active users (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) FROM contexts
                    WHERE datetime(last_active) > datetime('now', '-1 day')
                """)
                active_users = cursor.fetchone()[0]

                # Recent users (last hour)
                cursor.execute("""
                    SELECT user_id, last_active
                    FROM contexts
                    WHERE datetime(last_active) > datetime('now', '-1 hour')
                    ORDER BY last_active DESC
                    LIMIT 10
                """)
                recent_users = [
                    {"user_id": row[0], "last_active": row[1]}
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
                    "total_users": total_users,
                    "active_users_24h": active_users,
                    "recent_users": recent_users,
                    "total_messages": total_messages,
                    "messages_today": messages_today
                }
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {}

    def get_heartbeat_stats(self) -> Dict[str, Any]:
        """Get heartbeat statistics"""
        try:
            import sqlite3

            with sqlite3.connect(self.assistant.db_path) as conn:
                cursor = conn.cursor()

                # Users with heartbeat enabled
                cursor.execute("""
                    SELECT COUNT(*) FROM contexts WHERE heartbeat_enabled = 1
                """)
                enabled_count = cursor.fetchone()[0]

                # Recent heartbeat activity
                cursor.execute("""
                    SELECT user_id, heartbeat_enabled, heartbeat_interval, last_heartbeat
                    FROM contexts
                    WHERE heartbeat_enabled = 1
                    ORDER BY last_heartbeat DESC
                    LIMIT 10
                """)
                heartbeat_users = [
                    {
                        "user_id": row[0],
                        "interval": row[2],
                        "last_heartbeat": row[3]
                    }
                    for row in cursor.fetchall()
                ]

                # Recent heartbeat logs
                cursor.execute("""
                    SELECT user_id, timestamp, result
                    FROM heartbeat_log
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                recent_logs = [
                    {
                        "user_id": row[0],
                        "timestamp": row[1],
                        "result": row[2][:100] if row[2] else "N/A"
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    "enabled_count": enabled_count,
                    "heartbeat_users": heartbeat_users,
                    "recent_logs": recent_logs
                }
        except Exception as e:
            logger.error(f"Failed to get heartbeat stats: {e}")
            return {}

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": self.get_system_stats(),
            "users": self.get_user_stats(),
            "heartbeat": self.get_heartbeat_stats(),
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
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 30px;
            border-bottom: 1px solid #30363d;
            padding-bottom: 20px;
        }

        h1 {
            font-size: 32px;
            font-weight: 600;
            color: #58a6ff;
        }

        .subtitle {
            color: #8b949e;
            margin-top: 5px;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }

        .status-online {
            background: #1f6feb;
            color: white;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 20px;
        }

        .card h2 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #f0f6fc;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #21262d;
        }

        .stat:last-child {
            border-bottom: none;
        }

        .stat-label {
            color: #8b949e;
        }

        .stat-value {
            font-weight: 600;
            color: #f0f6fc;
        }

        .list-item {
            padding: 10px;
            margin: 5px 0;
            background: #0d1117;
            border-radius: 6px;
            font-size: 13px;
        }

        .list-item-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }

        .list-item-meta {
            color: #8b949e;
            font-size: 12px;
        }

        .progress-bar {
            width: 100%;
            height: 6px;
            background: #21262d;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 5px;
        }

        .progress-fill {
            height: 100%;
            background: #58a6ff;
            transition: width 0.3s ease;
        }

        .progress-fill.warning {
            background: #f85149;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #8b949e;
        }

        .refresh-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #3fb950;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .icon {
            width: 16px;
            height: 16px;
        }

        .test-section {
            margin-top: 20px;
            padding: 20px;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
        }

        .test-form {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        input, button {
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #30363d;
            background: #0d1117;
            color: #c9d1d9;
            font-size: 14px;
        }

        input {
            flex: 1;
        }

        button {
            background: #1f6feb;
            border-color: #1f6feb;
            color: white;
            cursor: pointer;
            font-weight: 600;
        }

        button:hover {
            background: #1a5cd7;
        }

        .test-result {
            margin-top: 10px;
            padding: 10px;
            border-radius: 6px;
            background: #0d1117;
            display: none;
        }

        .test-result.show {
            display: block;
        }
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
            <div class="subtitle">Real-time monitoring • Updated every 5 seconds</div>
        </header>

        <div class="grid">
            <!-- System Stats -->
            <div class="card">
                <h2>
                    <svg class="icon" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"/>
                    </svg>
                    System Status
                </h2>
                <div class="stat">
                    <span class="stat-label">CPU Usage</span>
                    <span class="stat-value" id="cpu">--%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar"></div>
                </div>
                <div class="stat">
                    <span class="stat-label">Memory Usage</span>
                    <span class="stat-value" id="memory">--%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar"></div>
                </div>
                <div class="stat">
                    <span class="stat-label">Disk Free</span>
                    <span class="stat-value" id="disk">-- GB</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Process Memory</span>
                    <span class="stat-value" id="process-mem">-- MB</span>
                </div>
            </div>

            <!-- User Stats -->
            <div class="card">
                <h2>
                    <svg class="icon" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4Zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10Z"/>
                    </svg>
                    Users
                </h2>
                <div class="stat">
                    <span class="stat-label">Total Users</span>
                    <span class="stat-value" id="total-users">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Active (24h)</span>
                    <span class="stat-value" id="active-users">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Messages</span>
                    <span class="stat-value" id="total-messages">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Messages Today</span>
                    <span class="stat-value" id="messages-today">--</span>
                </div>
            </div>

            <!-- Heartbeat Stats -->
            <div class="card">
                <h2>
                    <svg class="icon" fill="currentColor" viewBox="0 0 16 16">
                        <path d="m8 2.748-.717-.737C5.6.281 2.514.878 1.4 3.053c-.523 1.023-.641 2.5.314 4.385.92 1.815 2.834 3.989 6.286 6.357 3.452-2.368 5.365-4.542 6.286-6.357.955-1.886.838-3.362.314-4.385C13.486.878 10.4.28 8.717 2.01L8 2.748ZM8 15C-7.333 4.868 3.279-3.04 7.824 1.143c.06.055.119.112.176.171a3.12 3.12 0 0 1 .176-.17C12.72-3.042 23.333 4.867 8 15Z"/>
                    </svg>
                    Heartbeat
                </h2>
                <div class="stat">
                    <span class="stat-label">Enabled Users</span>
                    <span class="stat-value" id="heartbeat-enabled">--</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Status</span>
                    <span class="stat-value" id="heartbeat-status">--</span>
                </div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="card">
            <h2>Recent Users (Last Hour)</h2>
            <div id="recent-users">
                <div class="empty-state">No recent activity</div>
            </div>
        </div>

        <!-- Recent Heartbeats -->
        <div class="card">
            <h2>Recent Heartbeat Checks</h2>
            <div id="recent-heartbeats">
                <div class="empty-state">No heartbeat activity</div>
            </div>
        </div>

        <!-- Quick Test -->
        <div class="test-section">
            <h2>Quick Test Message</h2>
            <div class="test-form">
                <input type="text" id="test-user" placeholder="User ID (e.g., test)" value="test">
                <input type="text" id="test-message" placeholder="Message" value="Hello!">
                <button onclick="sendTest()">Send Test</button>
            </div>
            <div class="test-result" id="test-result"></div>
        </div>
    </div>

    <script>
        const eventSource = new EventSource('/dashboard/stream');

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };

        eventSource.onerror = function() {
            console.error('SSE connection error');
        };

        function updateDashboard(data) {
            // System stats
            if (data.system) {
                document.getElementById('cpu').textContent =
                    data.system.cpu_percent?.toFixed(1) + '%' || '--%';
                document.getElementById('memory').textContent =
                    data.system.memory_percent?.toFixed(1) + '%' || '--%';
                document.getElementById('disk').textContent =
                    data.system.disk_free_gb?.toFixed(1) + ' GB' || '-- GB';
                document.getElementById('process-mem').textContent =
                    data.system.process_memory_mb?.toFixed(0) + ' MB' || '-- MB';

                // Progress bars
                const cpuBar = document.getElementById('cpu-bar');
                cpuBar.style.width = (data.system.cpu_percent || 0) + '%';
                cpuBar.className = 'progress-fill' +
                    (data.system.cpu_percent > 80 ? ' warning' : '');

                const memBar = document.getElementById('memory-bar');
                memBar.style.width = (data.system.memory_percent || 0) + '%';
                memBar.className = 'progress-fill' +
                    (data.system.memory_percent > 80 ? ' warning' : '');
            }

            // User stats
            if (data.users) {
                document.getElementById('total-users').textContent = data.users.total_users || 0;
                document.getElementById('active-users').textContent = data.users.active_users_24h || 0;
                document.getElementById('total-messages').textContent = data.users.total_messages || 0;
                document.getElementById('messages-today').textContent = data.users.messages_today || 0;

                // Recent users
                const recentUsersDiv = document.getElementById('recent-users');
                if (data.users.recent_users && data.users.recent_users.length > 0) {
                    recentUsersDiv.innerHTML = data.users.recent_users.map(user => `
                        <div class="list-item">
                            <div class="list-item-header">
                                <strong>${user.user_id}</strong>
                                <span class="list-item-meta">${formatTime(user.last_active)}</span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    recentUsersDiv.innerHTML = '<div class="empty-state">No recent activity</div>';
                }
            }

            // Heartbeat stats
            if (data.heartbeat) {
                document.getElementById('heartbeat-enabled').textContent = data.heartbeat.enabled_count || 0;
                document.getElementById('heartbeat-status').textContent =
                    data.scheduler_running ? 'Running' : 'Stopped';

                // Recent heartbeats
                const recentHBDiv = document.getElementById('recent-heartbeats');
                if (data.heartbeat.recent_logs && data.heartbeat.recent_logs.length > 0) {
                    recentHBDiv.innerHTML = data.heartbeat.recent_logs.map(log => `
                        <div class="list-item">
                            <div class="list-item-header">
                                <strong>${log.user_id}</strong>
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
            const diff = Math.floor((now - date) / 1000 / 60); // minutes

            if (diff < 1) return 'Just now';
            if (diff < 60) return diff + 'm ago';
            if (diff < 1440) return Math.floor(diff / 60) + 'h ago';
            return Math.floor(diff / 1440) + 'd ago';
        }

        async function sendTest() {
            const user = document.getElementById('test-user').value;
            const message = document.getElementById('test-message').value;
            const resultDiv = document.getElementById('test-result');

            resultDiv.textContent = 'Sending...';
            resultDiv.classList.add('show');

            try {
                const response = await fetch('/webhook', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user, message})
                });

                const data = await response.json();
                resultDiv.textContent = 'Response: ' + data.response;
            } catch (error) {
                resultDiv.textContent = 'Error: ' + error.message;
            }
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
