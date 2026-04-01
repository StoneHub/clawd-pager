#!/usr/bin/env python3
"""
Dashboard WebSocket Server - Real-time device monitoring.

Provides a web dashboard for monitoring the Clawd Pager in real-time:
- Live event stream (button presses, mode changes, etc.)
- Current device state (mode, display text, battery)
- Session recording controls
- Quick actions (send test alert, toggle dev mode)

Usage:
    python -m devtools.dashboard_server

    # Or with custom port
    python -m devtools.dashboard_server --port 8080

The dashboard will be available at http://localhost:8080
"""

import asyncio
import json
import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Dict, Any, List
from dataclasses import dataclass, asdict

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("aiohttp not installed. Run: pip install aiohttp")

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("anthropic not installed. Run: pip install anthropic")

from .event_logger import EventLogger, EventSource, PagerEvent, get_logger
from .session_manager import SessionManager, get_session_manager


# Persistence file for summaries
SUMMARIES_FILE = Path.home() / '.clawd' / 'pager_summaries.json'


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Dashboard")


@dataclass
class DeviceState:
    """Current state of the pager device."""
    display_mode: str = "UNKNOWN"
    display_text: str = ""
    battery_level: int = 0
    wifi_signal: int = 0
    button_a: bool = False
    button_b: bool = False
    connected: bool = False
    last_update: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class DashboardServer:
    """
    WebSocket server for real-time pager monitoring.

    Broadcasts events to all connected dashboard clients and provides
    REST API endpoints for querying historical data.
    """

    def __init__(self, event_logger: Optional[EventLogger] = None,
                 session_manager: Optional[SessionManager] = None,
                 host: str = '0.0.0.0', port: int = 8080):
        """
        Initialize the dashboard server.

        Args:
            event_logger: EventLogger instance
            session_manager: SessionManager instance
            host: Host to bind to
            port: Port to listen on
        """
        self.event_logger = event_logger or get_logger()
        self.session_manager = session_manager or get_session_manager()
        self.host = host
        self.port = port

        self.websockets: Set[web.WebSocketResponse] = set()
        self.device_state = DeviceState()
        self.app: Optional[web.Application] = None
        self._running = False
        
        # Activity summarization
        self.event_batch: List[PagerEvent] = []
        self.summaries: List[Dict[str, Any]] = []
        self.max_summaries = 20
        self.batch_size = 10
        self.batch_timeout_seconds = 300  # 5 minutes
        self._last_batch_time = datetime.now()
        self._batch_timer_task: Optional[asyncio.Task] = None
        self._batch_lock = asyncio.Lock()  # Prevent race conditions on batch operations
        
        # Initialize Anthropic client if available
        self.anthropic_client = None
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set - Haiku summarization disabled, using fallback")
            self.anthropic_client = None
        else:
            try:
                if HAS_ANTHROPIC:
                    self.anthropic_client = Anthropic(api_key=api_key)
                    logger.info("Haiku summarization enabled")
                else:
                    logger.warning("anthropic package not installed - summaries will be disabled")
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client: {e}")
                self.anthropic_client = None
        
        # Load persisted summaries
        self.load_summaries()

    def load_summaries(self):
        """Load summaries from disk on startup."""
        if SUMMARIES_FILE.exists():
            try:
                with open(SUMMARIES_FILE, 'r') as f:
                    self.summaries = json.load(f)
                logger.info(f"Loaded {len(self.summaries)} summaries from disk")
            except Exception as e:
                logger.warning(f"Could not load summaries: {e}")

    def save_summaries(self):
        """Save summaries to disk after adding new one."""
        try:
            SUMMARIES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SUMMARIES_FILE, 'w') as f:
                json.dump(self.summaries, f)
        except Exception as e:
            logger.warning(f"Could not save summaries: {e}")

    def setup_routes(self):
        """Configure HTTP routes and WebSocket endpoint."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp is required for dashboard server")

        self.app = web.Application()
        
        # Add CORS middleware to allow React dev server connections
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == 'OPTIONS':
                response = web.Response()
            else:
                response = await handler(request)
            
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        self.app.middlewares.append(cors_middleware)

        # REST API endpoints
        self.app.router.add_get('/api/events', self.handle_get_events)
        self.app.router.add_get('/api/events/recent', self.handle_get_recent_events)
        self.app.router.add_get('/api/sessions', self.handle_get_sessions)
        self.app.router.add_get('/api/session/{session_id}', self.handle_get_session)
        self.app.router.add_get('/api/state', self.handle_get_state)
        self.app.router.add_get('/api/summaries', self.handle_get_summaries)
        self.app.router.add_get('/api/usage/monthly', self.handle_get_monthly_usage)
        self.app.router.add_get('/api/subagents/status', self.handle_get_subagent_status)
        self.app.router.add_get('/api/activity/enhanced', self.handle_get_enhanced_activity)
        self.app.router.add_post('/api/log', self.handle_log_event)
        self.app.router.add_post('/api/session/start', self.handle_start_session)
        self.app.router.add_post('/api/session/end', self.handle_end_session)

        # Build & Deploy endpoints
        self.app.router.add_post('/api/build/compile', self.handle_compile)
        self.app.router.add_post('/api/build/upload', self.handle_upload)

        # Export endpoint (no session recording needed)
        self.app.router.add_get('/api/export/logs', self.handle_export_logs)

        # WebSocket for live updates
        self.app.router.add_get('/ws', self.websocket_handler)

        # Static files (dashboard UI)
        ui_path = Path(__file__).parent / 'dashboard_ui'
        if ui_path.exists():
            self.app.router.add_static('/static', ui_path)
            self.app.router.add_get('/', self.handle_index)

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve the dashboard HTML."""
        ui_path = Path(__file__).parent / 'dashboard_ui' / 'index.html'
        if ui_path.exists():
            return web.FileResponse(ui_path)
        return web.Response(text="Dashboard UI not found", status=404)

    async def handle_get_events(self, request: web.Request) -> web.Response:
        """Get events for a specific session."""
        session_id = request.query.get('session_id')
        if session_id:
            events = self.event_logger.get_session_events(session_id)
        else:
            events = self.event_logger.get_session_events()
        return web.json_response([e.to_dict() for e in events])

    async def handle_get_recent_events(self, request: web.Request) -> web.Response:
        """Get recent events across all sessions."""
        limit = int(request.query.get('limit', 100))
        event_type = request.query.get('type')
        events = self.event_logger.get_recent_events(limit, event_type)
        return web.json_response([e.to_dict() for e in events])

    async def handle_get_sessions(self, request: web.Request) -> web.Response:
        """List all recorded sessions."""
        sessions = self.session_manager.list_sessions()
        return web.json_response(sessions)

    async def handle_get_session(self, request: web.Request) -> web.Response:
        """Get details for a specific session."""
        session_id = request.match_info['session_id']
        try:
            session = self.session_manager.load_session(session_id)
            return web.json_response(session.to_dict())
        except FileNotFoundError:
            return web.json_response({"error": "Session not found"}, status=404)

    async def handle_get_state(self, request: web.Request) -> web.Response:
        """Get current device state."""
        return web.json_response(self.device_state.to_dict())

    async def handle_get_summaries(self, request: web.Request) -> web.Response:
        """Get recent activity summaries."""
        return web.json_response(self.summaries)

    async def handle_get_monthly_usage(self, request: web.Request) -> web.Response:
        """Get monthly token usage statistics from real OpenClaw session data."""
        try:
            from .openclaw_usage import get_monthly_usage
            usage_data = get_monthly_usage()
            return web.json_response(usage_data)
        except Exception as e:
            logger.error(f"Failed to get OpenClaw usage data: {e}")
            # Fallback to empty data on error
            from datetime import datetime
            return web.json_response({
                "current_month": {
                    "month": datetime.now().strftime("%Y-%m"),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_tokens": 0,
                    "cost": 0.0
                },
                "historical": [],
                "by_model": {}
            })

    async def handle_get_subagent_status(self, request: web.Request) -> web.Response:
        """Get status of active and recent sub-agents."""
        # TODO: Integrate with OpenClaw sessions API
        # For now, return mock data
        import random
        
        # Check if there are recent summaries to simulate activity
        has_activity = len(self.summaries) > 0
        
        active = []
        if has_activity and random.random() > 0.5:
            active.append({
                "id": "subagent-001",
                "name": "build-web-dashboard",
                "model": "claude-opus-4-6",
                "status": "active",
                "runtime": 145,
                "task": "Building React dashboard with 3 widgets"
            })
        
        recent = []
        if len(self.summaries) > 0:
            recent.append({
                "id": "subagent-000",
                "name": "research-dashboard",
                "model": "claude-sonnet-4-5",
                "status": "completed",
                "runtime": 89,
                "task": "Research modern dashboard frameworks",
                "result": "Recommended React + shadcn/ui stack"
            })
        
        return web.json_response({
            "active": active,
            "recent": recent,
            "queue": []
        })

    async def handle_get_enhanced_activity(self, request: web.Request) -> web.Response:
        """Get enhanced activity data with detailed context."""
        # Use existing summaries and events to build enhanced view
        recent_events = self.event_logger.get_recent_events(10, 'TOOL_START')
        
        # Extract tool calls from recent events
        tool_calls = []
        for event in recent_events[:5]:
            data = event.data or {}
            tool_call = {
                "tool": data.get('tool', 'unknown')
            }
            
            if 'file' in data:
                tool_call['file'] = data['file']
            if 'line' in data:
                tool_call['line'] = data['line']
            if 'command' in data:
                tool_call['command'] = data['command']
            if 'status' in data:
                tool_call['result'] = data['status']
                
            tool_calls.append(tool_call)
        
        # Use most recent summary if available
        summary_text = None
        timestamp = datetime.now().isoformat()
        if self.summaries:
            summary_text = self.summaries[0].get('text', '')
            timestamp = self.summaries[0].get('timestamp', timestamp)
        
        return web.json_response({
            "timestamp": timestamp,
            "user_prompt": "Build modern web dashboard with enhanced widgets",
            "agent_goal": "Create React app with 3 widgets, WebSocket connection, and responsive dark theme",
            "active_todos": [
                "Create React + Vite scaffold",
                "Install shadcn/ui + Tailwind",
                "Build 3 widget components",
                "Add backend API endpoints",
                "Test WebSocket connection"
            ],
            "tool_calls": tool_calls,
            "summary": summary_text or "Working on dashboard development"
        })

    async def handle_log_event(self, request: web.Request) -> web.Response:
        """Log an event from external source (dev scripts)."""
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        
        # Validate event_type
        VALID_EVENT_TYPES = ['TOOL_START', 'TOOL_END', 'AGENT_WORKING', 'AGENT_WAITING', 
                             'BUTTON_PRESS', 'BUTTON_RELEASE', 'DISPLAY_UPDATE', 'BATTERY_UPDATE']
        event_type = data.get('event_type', 'UNKNOWN')
        if event_type not in VALID_EVENT_TYPES:
            return web.json_response({"error": f"Invalid event_type: {event_type}"}, status=400)
        
        # Validate data size
        event_data = data.get('data', {})
        if len(json.dumps(event_data)) > 10000:  # 10KB limit
            return web.json_response({"error": "Event data too large"}, status=400)
        
        source = EventSource(data.get('source', 'user'))
        
        try:

            event = self.event_logger.log(source, event_type, event_data)

            # Update device state based on event type
            if event_type == "BATTERY_UPDATE":
                self.update_device_state(battery_level=event_data.get('level', 0))
            elif event_type == "DISPLAY_UPDATE":
                self.update_device_state(
                    display_mode=event_data.get('mode', ''),
                    display_text=event_data.get('text', '')
                )
            elif event_type == "BUTTON_PRESS":
                btn = event_data.get('button', '')
                if btn == 'A':
                    self.update_device_state(button_a=True)
                elif btn == 'B':
                    self.update_device_state(button_b=True)
            elif event_type == "BUTTON_RELEASE":
                btn = event_data.get('button', '')
                if btn == 'A':
                    self.update_device_state(button_a=False)
                elif btn == 'B':
                    self.update_device_state(button_b=False)
            elif event_type == "AGENT_WORKING":
                # Claude Code is using a tool - could update pager to show activity
                status = event_data.get('status', '')
                tool = event_data.get('tool', 'unknown')
                logger.info(f"Agent: {tool} {status}")
            elif event_type == "AGENT_WAITING":
                # Claude Code finished and waiting for user
                logger.info("Agent: waiting for user input")

            # Broadcast to connected dashboards
            await self.broadcast_event(event)
            
            # Add to batch for summarization (only relevant event types)
            if event_type in ['TOOL_START', 'TOOL_END', 'AGENT_WORKING', 'AGENT_WAITING']:
                async with self._batch_lock:
                    self.event_batch.append(event)
                
                # Check if we should summarize
                time_elapsed = (datetime.now() - self._last_batch_time).total_seconds()
                should_summarize = (
                    len(self.event_batch) >= self.batch_size or 
                    time_elapsed >= self.batch_timeout_seconds
                )
                
                if should_summarize:
                    asyncio.create_task(self.summarize_batch())
                elif self._batch_timer_task is None or self._batch_timer_task.done():
                    # Start/restart the batch timer
                    self._batch_timer_task = asyncio.create_task(self.batch_timer())

            return web.json_response({"status": "logged", "sequence": event.sequence})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_start_session(self, request: web.Request) -> web.Response:
        """Start a new recording session."""
        try:
            data = await request.json()
            notes = data.get('notes', '')
            session_id = self.session_manager.start_session(notes)
            return web.json_response({
                "status": "started",
                "session_id": session_id
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_end_session(self, request: web.Request) -> web.Response:
        """End the current recording session."""
        session_id = self.session_manager.end_session()
        if session_id:
            return web.json_response({
                "status": "ended",
                "session_id": session_id
            })
        return web.json_response({"status": "no_session"})

    async def handle_export_logs(self, request: web.Request) -> web.Response:
        """Export recent logs as markdown (no session recording needed)."""
        limit = int(request.query.get('limit', 200))
        events = self.event_logger.get_recent_events(limit)

        if not events:
            return web.Response(text="# No Events\n\nNo events recorded yet.", content_type='text/markdown')

        # Build markdown
        first_ts = events[-1].timestamp if events else "unknown"
        last_ts = events[0].timestamp if events else "unknown"

        md = f"""# Clawd Pager Event Log

**Exported**: {datetime.now().isoformat(timespec='seconds')}
**Events**: {len(events)}
**Time Range**: {first_ts} to {last_ts}

## Event Timeline

| Time | Type | Source | Details |
|------|------|--------|---------|
"""
        for event in reversed(events):  # Oldest first
            ts = event.timestamp
            if "T" in ts:
                ts = ts.split("T")[1][:12]  # Just time portion
            data = event.data or {}

            # Create summary based on event type
            if event.event_type == "DISPLAY_UPDATE":
                details = f"[{data.get('mode', '')}] {data.get('text', '')[:40]}"
            elif event.event_type == "BUTTON_PRESS":
                details = f"Button {data.get('button', '')} pressed"
            elif event.event_type == "BUTTON_RELEASE":
                details = f"Button {data.get('button', '')} ({data.get('duration_ms', 0):.0f}ms)"
            elif event.event_type == "MODE_CHANGE":
                details = f"{data.get('from_mode', '')} → {data.get('to_mode', '')}"
            elif event.event_type == "BATTERY_UPDATE":
                details = f"Battery: {data.get('level', '')}%"
            elif event.event_type == "ERROR":
                details = f"{data.get('error_type', '')}: {data.get('message', '')[:30]}"
            else:
                details = str(data)[:50] if data else ""

            md += f"| {ts} | {event.event_type} | {event.source} | {details} |\n"

        return web.Response(text=md, content_type='text/markdown',
                           headers={'Content-Disposition': f'attachment; filename="pager_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"'})

    async def handle_compile(self, request: web.Request) -> web.Response:
        """Compile ESPHome firmware."""
        import subprocess
        import time

        self.event_logger.log(EventSource.USER, "BUILD_START", {"yaml_file": "clawd-pager.yaml"})
        await self.broadcast({"type": "build_status", "status": "compiling"})

        start_time = time.time()
        yaml_path = Path(__file__).parent.parent / "clawd-pager.yaml"

        try:
            result = subprocess.run(
                ["esphome", "compile", str(yaml_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            duration = time.time() - start_time
            success = result.returncode == 0

            self.event_logger.log(EventSource.USER, "BUILD_END", {
                "success": success,
                "duration_s": round(duration, 1)
            })

            await self.broadcast({
                "type": "build_status",
                "status": "done" if success else "failed",
                "duration_s": round(duration, 1)
            })

            return web.json_response({
                "success": success,
                "duration_s": round(duration, 1),
                "output": result.stdout[-2000:] if not success else ""
            })
        except subprocess.TimeoutExpired:
            return web.json_response({"success": False, "error": "Build timed out"})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)})

    async def handle_upload(self, request: web.Request) -> web.Response:
        """Upload firmware via OTA."""
        import subprocess
        import time

        device_ip = "192.168.50.85"
        self.event_logger.log(EventSource.USER, "OTA_START", {"target_ip": device_ip})
        await self.broadcast({"type": "build_status", "status": "uploading"})

        start_time = time.time()
        yaml_path = Path(__file__).parent.parent / "clawd-pager.yaml"

        try:
            result = subprocess.run(
                ["esphome", "upload", str(yaml_path), "--device", device_ip],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            duration = time.time() - start_time
            success = result.returncode == 0

            self.event_logger.log(EventSource.USER, "OTA_END", {
                "success": success,
                "duration_s": round(duration, 1)
            })

            await self.broadcast({
                "type": "build_status",
                "status": "uploaded" if success else "failed",
                "duration_s": round(duration, 1)
            })

            return web.json_response({
                "success": success,
                "duration_s": round(duration, 1)
            })
        except subprocess.TimeoutExpired:
            return web.json_response({"success": False, "error": "Upload timed out"})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)})

    async def batch_timer(self):
        """Timer to trigger batch summarization after timeout."""
        try:
            await asyncio.sleep(self.batch_timeout_seconds)
            if self.event_batch:
                await self.summarize_batch()
        except asyncio.CancelledError:
            pass

    async def summarize_batch(self):
        """Summarize the current batch of events using Claude Haiku."""
        if not self.event_batch:
            return
        
        # Cancel any pending timer
        if self._batch_timer_task and not self._batch_timer_task.done():
            self._batch_timer_task.cancel()
            self._batch_timer_task = None
        
        # Take the current batch and clear it
        async with self._batch_lock:
            batch = self.event_batch[:]
            self.event_batch.clear()
        self._last_batch_time = datetime.now()
        
        logger.info(f"Summarizing batch of {len(batch)} events...")
        
        # Check if Anthropic is available
        if not self.anthropic_client:
            logger.warning("Anthropic client not available, skipping summarization")
            return
        
        try:
            # Build event context for Haiku
            event_text = []
            for event in batch:
                ts = event.timestamp.split('T')[1][:8] if 'T' in event.timestamp else event.timestamp
                event_type = event.event_type
                data = event.data or {}
                
                if event_type == 'TOOL_START':
                    tool = data.get('tool', 'unknown')
                    command = data.get('command', '')
                    event_text.append(f"[{ts}] TOOL_START: {tool} - {command}")
                elif event_type == 'TOOL_END':
                    tool = data.get('tool', 'unknown')
                    status = data.get('status', 'unknown')
                    event_text.append(f"[{ts}] TOOL_END: {tool} - {status}")
                elif event_type == 'AGENT_WORKING':
                    tool = data.get('tool', 'unknown')
                    status = data.get('status', '')
                    event_text.append(f"[{ts}] AGENT_WORKING: {tool} {status}")
                elif event_type == 'AGENT_WAITING':
                    event_text.append(f"[{ts}] AGENT_WAITING: Ready for user input")
                else:
                    event_text.append(f"[{ts}] {event_type}: {data}")
            
            events_str = '\n'.join(event_text)
            
            # Call Claude Haiku
            try:
                message = self.anthropic_client.messages.create(
                    model="claude-3-7-haiku-20250219",  # Updated model
                    max_tokens=150,
                    timeout=30.0,  # 30 second timeout to prevent hanging
                    messages=[{
                        "role": "user",
                        "content": f"""Summarize these tool events into ONE concise human-readable sentence describing the task completed. Be specific but brief.

Events:
{events_str}

Respond with ONLY the summary sentence, nothing else."""
                    }]
                )
                
                summary_text = message.content[0].text.strip()
            except Exception as api_error:
                # Fallback to simple summary if API fails
                logger.warning(f"API call failed: {api_error}, using fallback summary")
                tool_names = set()
                for event in batch:
                    if event.event_type == 'TOOL_START':
                        tool = event.data.get('tool', 'unknown')
                        tool_names.add(tool)
                
                if tool_names:
                    summary_text = f"Completed {len(batch)} operations using {', '.join(tool_names)}"
                else:
                    summary_text = f"Completed {len(batch)} agent operations"
            
            # Create summary object
            summary = {
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "text": summary_text,
                "event_count": len(batch)
            }
            
            # Add to summaries (rolling buffer)
            self.summaries.insert(0, summary)
            if len(self.summaries) > self.max_summaries:
                self.summaries = self.summaries[:self.max_summaries]
            
            # Persist summaries to disk
            self.save_summaries()
            
            logger.info(f"Generated summary: {summary_text}")
            
            # Broadcast summary to dashboards
            await self.broadcast({
                "type": "summary",
                "data": summary
            })
            
        except Exception as e:
            logger.error(f"Failed to summarize batch: {e}")

    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for live updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.add(ws)
        logger.info(f"Dashboard client connected ({len(self.websockets)} total)")

        # Send current state on connect
        await ws.send_json({
            "type": "state",
            "data": self.device_state.to_dict()
        })

        # Send recent events
        recent = self.event_logger.get_recent_events(20)
        for event in reversed(recent):
            await ws.send_json({
                "type": "event",
                "data": event.to_dict()
            })

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_ws_message(ws, data)
                    except json.JSONDecodeError:
                        pass
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"Dashboard client disconnected ({len(self.websockets)} total)")

        return ws

    async def handle_ws_message(self, ws: web.WebSocketResponse, data: dict):
        """Handle incoming WebSocket messages from dashboards."""
        msg_type = data.get('type')

        if msg_type == 'ping':
            await ws.send_json({"type": "pong"})

        elif msg_type == 'start_session':
            notes = data.get('notes', '')
            session_id = self.session_manager.start_session(notes)
            await self.broadcast({
                "type": "session_started",
                "session_id": session_id
            })

        elif msg_type == 'end_session':
            session_id = self.session_manager.end_session()
            await self.broadcast({
                "type": "session_ended",
                "session_id": session_id
            })

        elif msg_type == 'add_note':
            note = data.get('note', '')
            self.session_manager.add_note(note)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected WebSocket clients."""
        if not self.websockets:
            return

        msg_str = json.dumps(message)
        dead_sockets = set()

        for ws in self.websockets:
            try:
                await ws.send_str(msg_str)
            except Exception:
                dead_sockets.add(ws)

        # Clean up disconnected sockets
        self.websockets -= dead_sockets

    async def broadcast_event(self, event: PagerEvent):
        """Broadcast an event to all dashboards."""
        await self.broadcast({
            "type": "event",
            "data": event.to_dict()
        })

    def update_device_state(self, **kwargs):
        """Update device state and broadcast to dashboards."""
        for key, value in kwargs.items():
            if hasattr(self.device_state, key):
                setattr(self.device_state, key, value)

        self.device_state.last_update = datetime.now().isoformat(timespec='milliseconds')

        # Schedule broadcast
        asyncio.create_task(self.broadcast({
            "type": "state",
            "data": self.device_state.to_dict()
        }))

    async def run(self):
        """Start the dashboard server."""
        self.setup_routes()
        self._running = True

        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Dashboard server running at http://{self.host}:{self.port}")
        logger.info(f"WebSocket endpoint: ws://{self.host}:{self.port}/ws")

        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            await runner.cleanup()

    def stop(self):
        """Stop the server."""
        self._running = False


# Singleton instance
_dashboard_server: Optional[DashboardServer] = None


def get_dashboard_server(port: int = 8080) -> DashboardServer:
    """Get or create the global DashboardServer instance."""
    global _dashboard_server
    if _dashboard_server is None:
        _dashboard_server = DashboardServer(port=port)
    return _dashboard_server


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Clawd Pager Development Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    if not HAS_AIOHTTP:
        print("Error: aiohttp is required. Install with: pip install aiohttp")
        return 1

    server = DashboardServer(host=args.host, port=args.port)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Dashboard server stopped")

    return 0


if __name__ == '__main__':
    exit(main())
