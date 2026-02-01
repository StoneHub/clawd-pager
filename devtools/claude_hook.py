#!/usr/bin/env python3
"""
Claude Code Hook - Emits agent activity events to the Clawd Pager.

This script is called by Claude Code's hook system (PreToolUse, PostToolUse, etc.)
to notify the pager when the agent is actively working.

Usage:
    claude_hook.py <event_type> [tool_name] [extra_data]
    claude_hook.py ask "Your question here?" [--timeout 30]

Events:
    TOOL_START <tool>    - Agent started using a tool
    TOOL_END <tool>      - Agent finished using a tool
    WAITING              - Agent is waiting for user input
    QUESTION <question>  - Agent is asking user a yes/no question

Special Commands:
    ask <question>       - Send question to pager and WAIT for response
                           Returns "yes" or "no" to stdout

Environment:
    BRIDGE_URL - Bridge API URL (default: http://192.168.50.50:8081)
    DASHBOARD_URL - Dashboard server URL (default: http://192.168.50.50:8080)
"""

import sys
import os
import json
import time
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


def poll_for_response(timeout: int = 60) -> str:
    """Poll the bridge for a response from the user."""
    start_time = time.time()
    poll_interval = 0.5  # Check every 500ms

    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(
                f"{BRIDGE_URL}/response",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "ok" and "response" in data:
                    return data["response"].get("response", "")
        except (urllib.error.URLError, TimeoutError, ConnectionRefusedError, json.JSONDecodeError):
            pass

        time.sleep(poll_interval)

    return ""  # Timeout with no response


def ask_and_wait(question: str, timeout: int = 60) -> str:
    """
    Send a question to the pager and wait for the user's response.
    Returns "yes", "no", or "" (timeout).
    """
    # Send the question to the bridge
    success = send_to_bridge("QUESTION", None, question)
    if not success:
        sys.stderr.write("Failed to send question to pager\n")
        return ""

    send_to_dashboard("QUESTION", {"question": question, "waiting": True})

    # Poll for response
    response = poll_for_response(timeout)

    send_to_dashboard("QUESTION_ANSWERED", {"question": question, "response": response})

    return response


def main():
    if len(sys.argv) < 2:
        print("Usage: claude_hook.py <event_type> [tool_name] [extra_data]")
        print("       claude_hook.py ask \"Your question?\" [--timeout 30]")
        sys.exit(1)

    command = sys.argv[1].lower()

    # Special "ask" command - send question and wait for response
    if command == "ask":
        if len(sys.argv) < 3:
            print("Usage: claude_hook.py ask \"Your question?\" [--timeout 30]")
            sys.exit(1)

        question = sys.argv[2]
        timeout = 60  # Default timeout

        # Parse optional --timeout argument
        if len(sys.argv) > 3 and sys.argv[3] == "--timeout":
            try:
                timeout = int(sys.argv[4])
            except (IndexError, ValueError):
                pass

        response = ask_and_wait(question, timeout)
        if response:
            print(response)  # Output to stdout for Claude Code to read
            sys.exit(0)
        else:
            sys.stderr.write("No response received (timeout)\n")
            sys.exit(1)

    # Regular event handling
    event_type = command.upper()
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
