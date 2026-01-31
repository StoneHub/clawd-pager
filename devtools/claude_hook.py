#!/usr/bin/env python3
"""
Claude Code Hook - Emits agent activity events to the Clawd Pager.

This script is called by Claude Code's hook system (PreToolUse, PostToolUse, etc.)
to notify the pager when the agent is actively working.

Usage:
    claude_hook.py <event_type> [tool_name]

Events:
    TOOL_START <tool>  - Agent started using a tool
    TOOL_END <tool>    - Agent finished using a tool
    WAITING            - Agent is waiting for user input

Environment:
    BRIDGE_URL - Bridge API URL (default: http://localhost:8081)
    DASHBOARD_URL - Dashboard server URL (default: http://localhost:8080)
"""

import sys
import os
import json
import urllib.request
import urllib.error

BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://localhost:8081")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8080")


def send_to_bridge(event_type: str, tool: str = None):
    """Send event directly to the bridge to update pager."""
    payload = {"event_type": event_type}
    if tool:
        payload["tool"] = tool

    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}/agent",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError):
        return False


def send_to_dashboard(event_type: str, data: dict = None):
    """Send event to dashboard for logging."""
    payload = {
        "source": "claude_code",
        "event_type": event_type,
        "data": data or {}
    }

    try:
        req = urllib.request.Request(
            f"{DASHBOARD_URL}/api/log",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError):
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: claude_hook.py <event_type> [tool_name]")
        sys.exit(1)

    event_type = sys.argv[1].upper()
    tool_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Send to bridge (updates pager display)
    send_to_bridge(event_type, tool_name)

    # Also log to dashboard
    if event_type == "TOOL_START":
        send_to_dashboard("AGENT_WORKING", {"tool": tool_name, "status": "start"})
    elif event_type == "TOOL_END":
        send_to_dashboard("AGENT_WORKING", {"tool": tool_name, "status": "end"})
    elif event_type == "WAITING":
        send_to_dashboard("AGENT_WAITING", {})


if __name__ == "__main__":
    main()
