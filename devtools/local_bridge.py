#!/usr/bin/env python3
"""
Clawd Pager Local Bridge - Runs alongside Claude Code in WSL.

Connects to the M5StickC Plus pager over local WiFi using ESPHome's native API.
Receives hook events from Claude Code and translates them into pager display
updates, permission prompts, and alerts.

No Pi dependency. Just: laptop (WSL) ←WiFi→ pager.

Usage:
    pip install aioesphomeapi aiohttp
    python local_bridge.py                          # auto-discover via mDNS
    python local_bridge.py --pager-ip 192.168.50.85 # explicit IP
    PAGER_IP=192.168.50.85 python local_bridge.py   # env var

Architecture:
    Claude Code hooks → HTTP :8081 → this bridge → ESPHome API :6053 → Pager
"""

import asyncio
import argparse
import json
import logging
import os
import time
import uuid
from typing import Optional

try:
    from aiohttp import web
except ImportError:
    print("Missing aiohttp. Install: pip install aiohttp")
    raise

try:
    from aioesphomeapi import APIClient, EntityState
except ImportError:
    print("Missing aioesphomeapi. Install: pip install aioesphomeapi")
    raise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bridge")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PAGER_IP = os.environ.get("PAGER_IP", "")
DEFAULT_PAGER_PORT = int(os.environ.get("PAGER_PORT", "6053"))
DEFAULT_BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8081"))
ESPHOME_PASSWORD = os.environ.get("ESPHOME_PASSWORD", "")
ESPHOME_NOISE_PSK = os.environ.get("ESPHOME_NOISE_PSK", "")

# Mode the bridge sends to firmware when a tool ends and nothing is pending
IDLE_DELAY = 3.0  # seconds before reverting to IDLE after last tool ends

# ---------------------------------------------------------------------------
# Pager connection
# ---------------------------------------------------------------------------

class PagerConnection:
    """Manages the ESPHome native API connection to the pager."""

    def __init__(self, host: str, port: int = 6053):
        self.host = host
        self.port = port
        self.client: Optional[APIClient] = None
        self.connected = False
        self._display_mode = "IDLE"
        self._reconnect_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to pager via ESPHome native API."""
        log.info("Connecting to pager at %s:%d ...", self.host, self.port)
        self.client = APIClient(
            self.host,
            self.port,
            password=ESPHOME_PASSWORD,
            noise_psk=ESPHOME_NOISE_PSK or None,
        )
        try:
            await self.client.connect(login=True)
            self.connected = True
            log.info("Connected to pager!")

            # Subscribe to state changes (button presses change display_mode)
            await self.client.subscribe_states(self._on_state_change)
        except Exception as e:
            log.error("Failed to connect: %s", e)
            self.connected = False
            raise

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.connected = False

    def _on_state_change(self, state: EntityState):
        """Track display_mode changes from the pager (button presses etc)."""
        # EntityState is a generic container; text_sensor states have .state
        if hasattr(state, "state") and isinstance(state.state, str):
            # We care about display_mode changes for permission tracking
            if state.state in (
                "PERM_APPROVED", "PERM_DENIED",
                "IDLE", "DOCKED", "LISTENING", "PROCESSING",
            ):
                old = self._display_mode
                self._display_mode = state.state
                if old != state.state:
                    log.info("Pager mode: %s -> %s", old, state.state)

    @property
    def display_mode(self) -> str:
        return self._display_mode

    async def set_display(self, text: str, mode: str):
        """Call the pager's set_display service."""
        if not self.connected:
            log.warning("Not connected — dropping set_display(%s, %s)", mode, text[:30])
            return
        try:
            await self.client.execute_service(
                # ESPHome service: esphome.clawd_pager_set_display
                # Service name format: {node_name}_{service_name}
                self._find_service("set_display"),
                data={"my_text": text, "my_mode": mode},
            )
            self._display_mode = mode.replace("SILENT_", "")
        except Exception as e:
            log.error("set_display failed: %s", e)

    async def alert(self, text: str):
        """Call the pager's alert service."""
        if not self.connected:
            return
        try:
            await self.client.execute_service(
                self._find_service("alert"),
                data={"my_text": text},
            )
        except Exception as e:
            log.error("alert failed: %s", e)

    def _find_service(self, name: str):
        """Find a service by suffix in the services list."""
        # aioesphomeapi stores services after connect; we construct the key
        # The service domain is "esphome" and the name is "{node}_{service}"
        from aioesphomeapi import UserService, UserServiceArg
        if name == "set_display":
            return UserService(
                name="clawd_pager_set_display",
                key=0,
                args=[
                    UserServiceArg(name="my_text", type=3),  # 3 = string
                    UserServiceArg(name="my_mode", type=3),
                ],
            )
        elif name == "alert":
            return UserService(
                name="clawd_pager_alert",
                key=0,
                args=[
                    UserServiceArg(name="my_text", type=3),
                ],
            )
        raise ValueError(f"Unknown service: {name}")


# ---------------------------------------------------------------------------
# Permission tracker
# ---------------------------------------------------------------------------

class PermissionTracker:
    """Tracks pending permission requests and their responses."""

    def __init__(self):
        self._pending: dict[str, dict] = {}

    def create(self, tool: str, command: str, timeout: int = 90) -> str:
        """Create a new permission request, return its ID."""
        req_id = str(uuid.uuid4())[:8]
        self._pending[req_id] = {
            "tool": tool,
            "command": command,
            "status": "pending",
            "created": time.time(),
            "timeout": timeout,
        }
        return req_id

    def resolve(self, req_id: str, approved: bool):
        """Mark a permission request as approved or denied."""
        if req_id in self._pending:
            self._pending[req_id]["status"] = "approved" if approved else "denied"
            log.info("Permission %s: %s", req_id, "APPROVED" if approved else "DENIED")

    def get_status(self, req_id: str) -> Optional[str]:
        """Get current status of a permission request."""
        req = self._pending.get(req_id)
        if not req:
            return None
        # Check for timeout
        if req["status"] == "pending" and time.time() - req["created"] > req["timeout"]:
            req["status"] = "expired"
        return req["status"]

    @property
    def active_id(self) -> Optional[str]:
        """Get the ID of the currently pending request (if any)."""
        for rid, req in self._pending.items():
            if req["status"] == "pending":
                elapsed = time.time() - req["created"]
                if elapsed < req["timeout"]:
                    return rid
        return None

    def cleanup(self):
        """Remove expired/resolved requests older than 5 minutes."""
        cutoff = time.time() - 300
        self._pending = {
            k: v for k, v in self._pending.items()
            if v["created"] > cutoff
        }


# ---------------------------------------------------------------------------
# Bridge HTTP server
# ---------------------------------------------------------------------------

class BridgeServer:
    """HTTP server that receives Claude Code hook events."""

    def __init__(self, pager: PagerConnection):
        self.pager = pager
        self.permissions = PermissionTracker()
        self._idle_task: Optional[asyncio.Task] = None
        self._last_tool_end = 0.0

    def build_app(self) -> web.Application:
        app = web.Application()
        app.router.add_post("/agent", self.handle_agent)
        app.router.add_post("/permission", self.handle_permission)
        app.router.add_get("/permission/{req_id}", self.handle_permission_poll)
        app.router.add_post("/device/display", self.handle_device_display)
        app.router.add_post("/device/alert", self.handle_device_alert)
        app.router.add_get("/status", self.handle_status)
        app.router.add_get("/health", self.handle_health)
        return app

    # --- Agent tool events (from claude_hook.py) ---

    async def handle_agent(self, request: web.Request) -> web.Response:
        """Handle tool start/end events from Claude Code hooks."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "bad json"}, status=400)

        event_type = data.get("event_type", "")
        tool = data.get("tool", "?")

        if event_type == "TOOL_START":
            display_mode = data.get("display_mode", "AGENT")
            display_text = data.get("display_text", tool)
            display_sub = data.get("display_sub", "")
            code_preview = data.get("code_preview", "")

            # Build multi-line message for pager
            lines = [display_text]
            if display_sub:
                lines.append(display_sub)
            if code_preview:
                lines.append(code_preview)
            message = "\n".join(lines)

            # Send with SILENT_ prefix to avoid beeping on every tool
            await self.pager.set_display(message, f"SILENT_{display_mode}")

            # Cancel any pending idle revert
            if self._idle_task and not self._idle_task.done():
                self._idle_task.cancel()

            log.info("TOOL_START: %s → %s", tool, display_mode)

        elif event_type == "TOOL_END":
            self._last_tool_end = time.time()
            # Schedule idle revert after delay (gets cancelled if another tool starts)
            if self._idle_task and not self._idle_task.done():
                self._idle_task.cancel()
            self._idle_task = asyncio.create_task(self._delayed_idle())

        elif event_type == "WAITING":
            await self.pager.set_display("READY", "SILENT_IDLE")
            log.info("Session idle")

        return web.json_response({"ok": True})

    async def _delayed_idle(self):
        """Revert to IDLE after a delay if no new tools start."""
        await asyncio.sleep(IDLE_DELAY)
        await self.pager.set_display("CLAWDBOT READY", "SILENT_IDLE")

    # --- Permission flow (from permission_handler.py) ---

    async def handle_permission(self, request: web.Request) -> web.Response:
        """Handle permission request — show on pager, return request ID."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "bad json"}, status=400)

        tool = data.get("tool", "Unknown")
        command = data.get("command", "")
        description = data.get("description", "")
        timeout = data.get("timeout", 90)

        req_id = self.permissions.create(tool, command, timeout)

        # Build permission display text
        message = f"APPROVE?\n{tool}\n{command}"
        await self.pager.set_display(message, "PERMISSION")

        log.info("PERMISSION REQUEST %s: %s — %s", req_id, tool, command[:50])
        return web.json_response({"request_id": req_id})

    async def handle_permission_poll(self, request: web.Request) -> web.Response:
        """Poll for permission response (button press on pager)."""
        req_id = request.match_info["req_id"]

        # Check if pager mode changed to PERM_APPROVED or PERM_DENIED
        pager_mode = self.pager.display_mode
        if pager_mode == "PERM_APPROVED":
            self.permissions.resolve(req_id, approved=True)
        elif pager_mode == "PERM_DENIED":
            self.permissions.resolve(req_id, approved=False)

        status = self.permissions.get_status(req_id)
        if status is None:
            return web.json_response({"error": "not found"}, status=404)

        return web.json_response({"status": status, "request_id": req_id})

    # --- Direct device control (from /pager slash command) ---

    async def handle_device_display(self, request: web.Request) -> web.Response:
        data = await request.json()
        text = data.get("text", "")
        mode = data.get("mode", "RESPONSE")
        await self.pager.set_display(text, mode)
        return web.json_response({"ok": True})

    async def handle_device_alert(self, request: web.Request) -> web.Response:
        data = await request.json()
        text = data.get("text", "")
        await self.pager.alert(text)
        return web.json_response({"ok": True})

    # --- Status / health ---

    async def handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "connected": self.pager.connected,
            "display_mode": self.pager.display_mode,
            "active_permission": self.permissions.active_id,
        })

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "pager": self.pager.connected})


# ---------------------------------------------------------------------------
# mDNS discovery
# ---------------------------------------------------------------------------

async def discover_pager() -> Optional[str]:
    """Try to discover pager via mDNS (clawd-pager.local)."""
    import socket
    try:
        ip = socket.gethostbyname("clawd-pager.local")
        log.info("Discovered pager via mDNS: %s", ip)
        return ip
    except socket.gaierror:
        log.warning("mDNS discovery failed for clawd-pager.local")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(pager_ip: str, bridge_port: int):
    # Resolve pager IP
    if not pager_ip:
        pager_ip = await discover_pager()
    if not pager_ip:
        log.error("No pager IP. Use --pager-ip or set PAGER_IP env var.")
        return

    # Connect to pager
    pager = PagerConnection(pager_ip, DEFAULT_PAGER_PORT)
    try:
        await pager.connect()
    except Exception as e:
        log.error("Cannot connect to pager at %s: %s", pager_ip, e)
        log.info("Bridge will start anyway — reconnect when pager is available.")
        # TODO: background reconnect task

    # Start HTTP server
    bridge = BridgeServer(pager)
    app = bridge.build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", bridge_port)
    await site.start()

    log.info("=== Clawd Bridge running on http://0.0.0.0:%d ===", bridge_port)
    log.info("Pager: %s:%d (%s)", pager_ip, DEFAULT_PAGER_PORT,
             "connected" if pager.connected else "disconnected")

    # Keep running
    try:
        while True:
            bridge.permissions.cleanup()
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        pass
    finally:
        await pager.disconnect()
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clawd Pager Local Bridge")
    parser.add_argument("--pager-ip", default=DEFAULT_PAGER_IP,
                        help="Pager IP address (or set PAGER_IP env)")
    parser.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT,
                        help="Bridge HTTP port (default 8081)")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.pager_ip, args.port))
    except KeyboardInterrupt:
        log.info("Shutting down.")
