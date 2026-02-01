#!/usr/bin/env python3
"""
Claude Code Hook - Emits agent activity events to the Clawd Pager.

This script is called by Claude Code's hook system (PreToolUse, PostToolUse, etc.)
to notify the pager when the agent is actively working.

Usage:
    claude_hook.py <event_type> [tool_name] [extra_data]

Events:
    TOOL_START <tool>    - Agent started using a tool
    TOOL_END <tool>      - Agent finished using a tool
    WAITING              - Agent is waiting for user input
    QUESTION <question>  - Agent is asking user a yes/no question

Environment:
    BRIDGE_URL - Bridge API URL (default: http://192.168.50.50:8081)
    DASHBOARD_URL - Dashboard server URL (default: http://192.168.50.50:8080)
"""

import sys
import os
import json
import urllib.request
import urllib.error

# Bridge and Dashboard run on the Raspberry Pi, not localhost
PI_HOST = "192.168.50.50"
BRIDGE_URL = os.environ.get("BRIDGE_URL", f"http://{PI_HOST}:8081")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", f"http://{PI_HOST}:8080")


def send_to_bridge(event_type: str, tool: str = None, question: str = None):
    """Send event directly to the bridge to update pager."""
    payload = {"event_type": event_type}
    if tool:
        payload["tool"] = tool
    if question:
        payload["question"] = question

    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}/agent",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
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
        print("Usage: claude_hook.py <event_type> [tool_name] [extra_data]")
        sys.exit(1)

    event_type = sys.argv[1].upper()
    tool_name = sys.argv[2] if len(sys.argv) > 2 else None
    extra_data = sys.argv[3] if len(sys.argv) > 3 else None

    # Special handling for AskUserQuestion - send the question to pager
    if event_type == "TOOL_START" and tool_name == "AskUserQuestion":
        # The question text might be in extra_data or we just notify
        send_to_bridge("QUESTION", tool_name, extra_data or "Claude is asking...")
        send_to_dashboard("QUESTION", {"tool": tool_name, "question": extra_data})
        return

    # Send to bridge (updates pager display)
    send_to_bridge(event_type, tool_name)

    # Also log to dashboard
    if event_type == "TOOL_START":
        send_to_dashboard("AGENT_WORKING", {"tool": tool_name, "status": "start"})
    elif event_type == "TOOL_END":
        send_to_dashboard("AGENT_WORKING", {"tool": tool_name, "status": "end"})
    elif event_type == "WAITING":
        send_to_dashboard("AGENT_WAITING", {})
    elif event_type == "QUESTION":
        send_to_dashboard("QUESTION", {"question": tool_name})


if __name__ == "__main__":
    main()
