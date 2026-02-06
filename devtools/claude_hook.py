#!/usr/bin/env python3
"""
Claude Code Hook - Rich activity notifications for Clawd Pager.

Reads tool input from stdin JSON and sends meaningful details to the pager:
- Edit: shows filename + lines added/removed
- Write: shows "NEW FILE: filename" with line count
- Read: shows filename being read
- Bash: shows command preview
- Grep/Glob: shows search pattern
- Task: shows agent type

Usage:
    echo '{"tool_name":"Edit",...}' | claude_hook.py TOOL_START
    claude_hook.py TOOL_END Edit
    claude_hook.py WAITING
"""

import sys
import os
import json
import urllib.request
import urllib.error

# Bridge runs on the Raspberry Pi
PI_HOST = "192.168.50.50"
BRIDGE_URL = os.environ.get("BRIDGE_URL", f"http://{PI_HOST}:8081")


def send_to_bridge(event_data: dict):
    """Send rich event data to the bridge (fire-and-forget with short timeout)."""
    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}/agent",
            data=json.dumps(event_data).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        # Very short timeout - we don't need to wait for response
        # Just fire and continue, don't block the tool
        urllib.request.urlopen(req, timeout=0.5)
        return True
    except Exception:
        # Silent fail - don't slow down Claude Code
        return False


def count_lines(text: str) -> int:
    """Count lines in text."""
    if not text:
        return 0
    return text.count('\n') + (1 if not text.endswith('\n') else 0)


def get_filename(path: str) -> str:
    """Extract just the filename from a path."""
    if not path:
        return "?"
    return os.path.basename(path)


def extract_tool_details(tool_name: str, tool_input: dict) -> dict:
    """Extract meaningful display info from tool input."""
    details = {
        "event_type": "TOOL_START",
        "tool": tool_name,
        "display_mode": "AGENT",  # Default — firmware's generic agent mode
    }

    if tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        old_str = tool_input.get("old_string", "")
        new_str = tool_input.get("new_string", "")

        old_lines = count_lines(old_str)
        new_lines = count_lines(new_str)
        added = new_lines
        removed = old_lines

        filename = get_filename(file_path)
        details["display_text"] = f"{filename}"

        # Show both added and removed
        if added > 0 and removed > 0:
            details["display_sub"] = f"+{added} -{removed}"
            if added > removed:
                details["color"] = "green"
            elif removed > added:
                details["color"] = "red"
            else:
                details["color"] = "yellow"
        elif added > 0:
            details["display_sub"] = f"+{added}"
            details["color"] = "green"
        elif removed > 0:
            details["display_sub"] = f"-{removed}"
            details["color"] = "red"
        else:
            details["display_sub"] = "~"
            details["color"] = "yellow"

        # For small changes, include the actual code snippet
        total_lines = added + removed
        if total_lines <= 5 and new_str:
            # Clean up the code for display (first meaningful line)
            preview_lines = [l.strip() for l in new_str.split('\n') if l.strip()]
            if preview_lines:
                preview = preview_lines[0][:40]
                details["code_preview"] = preview

        details["display_mode"] = "AGENT_EDIT"

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")

        filename = get_filename(file_path)
        lines = count_lines(content)

        details["display_text"] = f"NEW: {filename}"
        details["display_sub"] = f"{lines} lines"
        details["display_mode"] = "AGENT_NEW"
        details["color"] = "cyan"

    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        filename = get_filename(file_path)

        details["display_text"] = f"READ {filename}"
        details["display_mode"] = "AGENT_READ"
        details["color"] = "blue"

    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        # Get first word (the actual command)
        cmd_parts = command.strip().split()
        cmd_name = cmd_parts[0] if cmd_parts else "bash"

        # Truncate long commands
        short_cmd = command[:40] + "..." if len(command) > 40 else command

        details["display_text"] = f"$ {cmd_name}"
        details["display_sub"] = short_cmd
        details["display_mode"] = "AGENT_BASH"
        details["color"] = "orange"

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", ".")

        short_pattern = pattern[:30] + "..." if len(pattern) > 30 else pattern

        details["display_text"] = f"GREP: {short_pattern}"
        details["display_sub"] = f"in {get_filename(path) or '.'}"
        details["display_mode"] = "AGENT_SEARCH"
        details["color"] = "purple"

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")

        details["display_text"] = f"FIND: {pattern[:35]}"
        details["display_mode"] = "AGENT_SEARCH"
        details["color"] = "purple"

    elif tool_name == "Task":
        agent_type = tool_input.get("subagent_type", "agent")
        description = tool_input.get("description", "")

        details["display_text"] = f"AGENT: {agent_type}"
        details["display_sub"] = description[:40] if description else ""
        details["display_mode"] = "AGENT_SUB"
        details["color"] = "magenta"

    elif tool_name == "WebSearch":
        query = tool_input.get("query", "")

        details["display_text"] = "WEB SEARCH"
        details["display_sub"] = query[:40] + "..." if len(query) > 40 else query
        details["display_mode"] = "AGENT_WEB"
        details["color"] = "cyan"

    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")
        # Extract domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
        except:
            domain = url[:30]

        details["display_text"] = "FETCHING"
        details["display_sub"] = domain
        details["display_mode"] = "AGENT_WEB"
        details["color"] = "cyan"

    elif tool_name == "TodoWrite":
        todos = tool_input.get("todos", [])
        in_progress = [t for t in todos if t.get("status") == "in_progress"]
        pending = [t for t in todos if t.get("status") == "pending"]

        # Get the active task name (truncated)
        active_task = ""
        if in_progress:
            active_task = in_progress[0].get("content", "")[:30]

        # Build display: show active task and count of pending
        details["display_text"] = active_task if active_task else "PLANNING"
        details["display_sub"] = f"{len(pending)} more pending"

        # Send up to 3 todo items for display
        todo_items = []
        for t in in_progress[:1]:  # Current task first
            todo_items.append(f"► {t.get('content', '')[:28]}")
        for t in pending[:2]:  # Then up to 2 pending
            todo_items.append(f"○ {t.get('content', '')[:28]}")

        details["todo_items"] = todo_items
        details["display_mode"] = "AGENT_PLAN"
        details["color"] = "yellow"

    elif tool_name == "AskUserQuestion":
        questions = tool_input.get("questions", [])
        if questions:
            q = questions[0].get("question", "Question?")
            details["display_text"] = "QUESTION"
            details["display_sub"] = q[:50] + "..." if len(q) > 50 else q
        else:
            details["display_text"] = "ASKING..."
        details["display_mode"] = "QUESTION"
        details["color"] = "white"

    else:
        # Generic fallback
        details["display_text"] = tool_name
        details["display_mode"] = "AGENT"

    return details


def main():
    # CRITICAL: Always exit 0 for hook events to avoid blocking tools

    if len(sys.argv) < 2:
        sys.exit(0)

    event_type = sys.argv[1].upper() if sys.argv[1] else ""
    tool_name_arg = sys.argv[2] if len(sys.argv) > 2 else None

    # Try to read JSON from stdin (Claude Code provides tool details)
    tool_input = {}
    tool_name = tool_name_arg

    try:
        # Non-blocking stdin read
        import select
        if select.select([sys.stdin], [], [], 0.0)[0]:
            stdin_data = sys.stdin.read()
            if stdin_data.strip():
                data = json.loads(stdin_data)
                tool_name = data.get("tool_name", tool_name_arg)
                tool_input = data.get("tool_input", {})
    except Exception:
        pass  # Use fallback if stdin parsing fails

    if event_type == "TOOL_START":
        # Extract rich details and send to pager
        details = extract_tool_details(tool_name or "Tool", tool_input)
        send_to_bridge(details)

    elif event_type == "TOOL_END":
        send_to_bridge({
            "event_type": "TOOL_END",
            "tool": tool_name or "Tool"
        })

    elif event_type == "WAITING":
        send_to_bridge({
            "event_type": "WAITING",
            "display_text": "READY",
            "display_mode": "IDLE"
        })

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Never block tools due to hook errors
        sys.stderr.write(f"Hook error (non-blocking): {e}\n")
        sys.exit(0)
