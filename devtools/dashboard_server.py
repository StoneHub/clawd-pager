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
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Dict, Any
from dataclasses import dataclass, asdict

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("aiohttp not installed. Run: pip install aiohttp")

from .event_logger import EventLogger, EventSource, PagerEvent, get_logger
from .session_manager import SessionManager, get_session_manager


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

    def setup_routes(self):
        """Configure HTTP routes and WebSocket endpoint."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp is required for dashboard server")

        self.app = web.Application()

        # REST API endpoints
        self.app.router.add_get('/api/events', self.handle_get_events)
        self.app.router.add_get('/api/events/recent', self.handle_get_recent_events)
        self.app.router.add_get('/api/sessions', self.handle_get_sessions)
        self.app.router.add_get('/api/session/{session_id}', self.handle_get_session)
        self.app.router.add_get('/api/state', self.handle_get_state)
        self.app.router.add_post('/api/log', self.handle_log_event)
        self.app.router.add_post('/api/session/start', self.handle_start_session)
        self.app.router.add_post('/api/session/end', self.handle_end_session)

        # Build & Deploy endpoints
        self.app.router.add_post('/api/build/compile', self.handle_compile)
        self.app.router.add_post('/api/build/upload', self.handle_upload)

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

    async def handle_log_event(self, request: web.Request) -> web.Response:
        """Log an event from external source (dev scripts)."""
        try:
            data = await request.json()
            source = EventSource(data.get('source', 'user'))
            event_type = data.get('event_type', 'UNKNOWN')
            event_data = data.get('data', {})

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
