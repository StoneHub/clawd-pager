#!/usr/bin/env python3
"""
Claude Code Permission Handler - Remote approval via Clawd Pager.

This hook intercepts PermissionRequest events and routes them to the pager
for remote yes/no approval. If the pager is unavailable or times out,
it returns an error that causes Claude Code to show the terminal prompt.

Usage:
    Reads PermissionRequest JSON from stdin
    Sends to bridge for pager display
    Waits for user response (button press)
    Returns allow/deny decision to Claude Code

Hook Configuration (.claude/settings.json):
    "hooks": {
        "PermissionRequest": [
            {
                "hooks": [{
                    "type": "command",
                    "command": "python3 /path/to/permission_handler.py",
                    "timeout": 120
                }]
            }
        ]
    }
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error

# Bridge runs on the Raspberry Pi
PI_HOST = "192.168.50.50"
BRIDGE_URL = os.environ.get("BRIDGE_URL", f"http://{PI_HOST}:8081")

# Timeout for waiting for pager response (seconds)
PERMISSION_TIMEOUT = int(os.environ.get("PERMISSION_TIMEOUT", "90"))


def send_permission_request(tool_name: str, command: str, description: str = "") -> str:
    """
    Send permission request to bridge and wait for pager response.

    Returns: "yes", "no", or "" (timeout/error)
    """
    payload = {
        "event_type": "PERMISSION_REQUEST",
        "tool": tool_name,
        "command": command,
        "description": description,
        "timeout": PERMISSION_TIMEOUT
    }

    try:
        # Send permission request to bridge
        req = urllib.request.Request(
            f"{BRIDGE_URL}/permission",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            request_id = data.get("request_id")
            if not request_id:
                sys.stderr.write("Bridge returned no request_id\n")
                return ""
    except Exception as e:
        sys.stderr.write(f"Failed to send permission request: {e}\n")
        return ""

    # Poll for response
    start_time = time.time()
    poll_interval = 0.5

    while time.time() - start_time < PERMISSION_TIMEOUT:
        try:
            req = urllib.request.Request(
                f"{BRIDGE_URL}/permission/{request_id}",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode())
                status = data.get("status")

                if status == "approved":
                    return "yes"
                elif status == "denied":
                    return "no"
                elif status == "pending":
                    pass  # Keep polling
                else:
                    sys.stderr.write(f"Unknown status: {status}\n")
                    return ""

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Request expired or not found
                sys.stderr.write("Permission request expired\n")
                return ""
            sys.stderr.write(f"HTTP error polling: {e}\n")
        except Exception as e:
            sys.stderr.write(f"Error polling for response: {e}\n")

        time.sleep(poll_interval)

    sys.stderr.write("Permission request timed out\n")
    return ""


def format_command_preview(tool_name: str, tool_input: dict) -> str:
    """Format a human-readable preview of what the tool will do."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        if desc:
            return f"{desc}\n$ {cmd[:100]}"
        return f"$ {cmd[:100]}"

    elif tool_name == "Edit":
        path = tool_input.get("file_path", "")
        filename = os.path.basename(path) if path else "file"
        return f"Edit: {filename}"

    elif tool_name == "Write":
        path = tool_input.get("file_path", "")
        filename = os.path.basename(path) if path else "file"
        return f"Create: {filename}"

    elif tool_name == "Read":
        path = tool_input.get("file_path", "")
        filename = os.path.basename(path) if path else "file"
        return f"Read: {filename}"

    else:
        return f"{tool_name}"


def main():
    """Handle a PermissionRequest from Claude Code."""

    # Read permission request from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to parse stdin JSON: {e}\n")
        # Exit non-zero to let Claude Code show terminal prompt
        sys.exit(1)

    tool_name = input_data.get("tool_name", "Unknown")
    tool_input = input_data.get("tool_input", {})

    # Format human-readable preview
    preview = format_command_preview(tool_name, tool_input)
    description = tool_input.get("description", "")

    # Send to pager and wait for response
    response = send_permission_request(tool_name, preview, description)

    if response == "yes":
        # User approved - return allow decision
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": "allow"
                }
            }
        }
        print(json.dumps(decision))
        sys.exit(0)

    elif response == "no":
        # User denied - return deny decision
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": "deny",
                    "message": "Denied via pager"
                }
            }
        }
        print(json.dumps(decision))
        sys.exit(0)

    else:
        # Timeout or error - exit non-zero to show terminal prompt
        sys.stderr.write("No response from pager, falling back to terminal\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"Permission handler error: {e}\n")
        sys.exit(1)
