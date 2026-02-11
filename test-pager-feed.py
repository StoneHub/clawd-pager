#!/usr/bin/env python3
"""
Test Pager Feed WebSocket Connection

This script tests the WebSocket feed from dashboard_server.py
before integrating into the screensaver dashboard.

Usage:
    ./test-pager-feed.py

Expected Output:
    - Connection established message
    - Initial state message
    - Recent events (last 20)
    - Live events as they occur

To trigger test events:
    # In another terminal:
    curl -X POST http://localhost:8081/agent \
      -H "Content-Type: application/json" \
      -d '{"event_type":"TOOL_START","tool":"Edit","display_text":"test.py","display_sub":"+5 -2"}'
    
    curl -X POST http://localhost:8081/agent \
      -H "Content-Type: application/json" \
      -d '{"event_type":"WAITING"}'
"""

import asyncio
import websockets
import json
from datetime import datetime
import sys

# ANSI color codes for pretty output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


def format_timestamp(ts_str):
    """Extract and format timestamp for display."""
    try:
        if 'T' in ts_str:
            time_part = ts_str.split('T')[1]
            return time_part[:12]  # HH:MM:SS.mmm
        return ts_str
    except:
        return ts_str


def format_event(event):
    """Format event for console display with colors."""
    timestamp = format_timestamp(event.get('timestamp', ''))
    event_type = event.get('event_type', 'UNKNOWN')
    source = event.get('source', 'unknown')
    data = event.get('data', {})
    
    lines = []
    
    # Timestamp and source
    lines.append(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} "
        f"{Colors.BRIGHT_BLACK}({source}){Colors.RESET}"
    )
    
    # Event-specific formatting
    if event_type == 'TOOL_START':
        tool = data.get('tool', 'Tool')
        text = data.get('display_text', '')
        sub = data.get('display_sub', '')
        mode = data.get('display_mode', '')
        
        # Color based on tool type
        tool_colors = {
            'Edit': Colors.GREEN,
            'Write': Colors.BLUE,
            'Read': Colors.CYAN,
            'Bash': Colors.YELLOW,
            'Grep': Colors.MAGENTA,
            'Glob': Colors.MAGENTA,
            'Task': Colors.RED,
            'WebSearch': Colors.BRIGHT_CYAN,
        }
        color = tool_colors.get(tool, Colors.WHITE)
        
        lines.append(
            f"  {color}{Colors.BOLD}▶ {tool}{Colors.RESET} "
            f"{Colors.WHITE}{text}{Colors.RESET}"
        )
        if sub:
            lines.append(f"    {Colors.DIM}{sub}{Colors.RESET}")
        if mode:
            lines.append(f"    {Colors.BRIGHT_BLACK}[{mode}]{Colors.RESET}")
        
        # Show code preview if available
        code_preview = data.get('code_preview', '')
        if code_preview:
            lines.append(f"    {Colors.DIM}↳ {code_preview}{Colors.RESET}")
    
    elif event_type == 'TOOL_END':
        tool = data.get('tool', 'Tool')
        lines.append(
            f"  {Colors.GREEN}✓{Colors.RESET} "
            f"{Colors.DIM}{tool} completed{Colors.RESET}"
        )
    
    elif event_type == 'WAITING':
        lines.append(
            f"  {Colors.BRIGHT_GREEN}✓ Agent ready{Colors.RESET}"
        )
    
    elif event_type == 'QUESTION':
        question = data.get('question', 'Question?')
        lines.append(
            f"  {Colors.YELLOW}{Colors.BOLD}❓ Question{Colors.RESET}"
        )
        lines.append(f"    {Colors.WHITE}{question}{Colors.RESET}")
    
    elif event_type == 'BUTTON_PRESS':
        button = data.get('button', '')
        mode = data.get('mode', '')
        lines.append(
            f"  {Colors.BLUE}🔘 Button {button} pressed{Colors.RESET} "
            f"{Colors.DIM}[{mode}]{Colors.RESET}"
        )
    
    elif event_type == 'BUTTON_RELEASE':
        button = data.get('button', '')
        duration_ms = data.get('duration_ms', 0)
        duration_s = duration_ms / 1000 if duration_ms else 0
        lines.append(
            f"  {Colors.DIM}Button {button} released ({duration_s:.1f}s){Colors.RESET}"
        )
    
    elif event_type == 'VOICE_RESPONSE':
        transcript = data.get('transcript', '')
        response = data.get('response', '')
        lines.append(
            f"  {Colors.MAGENTA}{Colors.BOLD}🎤 Voice Command{Colors.RESET}"
        )
        if transcript:
            lines.append(f"    {Colors.WHITE}User: \"{transcript}\"{Colors.RESET}")
        if response:
            lines.append(f"    {Colors.CYAN}Bot: \"{response}\"{Colors.RESET}")
    
    elif event_type == 'USER_RESPONSE':
        answer = data.get('response', '')
        question = data.get('question', '')
        lines.append(
            f"  {Colors.GREEN}✓ User responded: {answer.upper()}{Colors.RESET}"
        )
        if question:
            lines.append(f"    {Colors.DIM}Q: {question[:50]}{Colors.RESET}")
    
    elif event_type == 'PERMISSION_NEEDED':
        reason = data.get('question', 'Permission needed')
        lines.append(
            f"  {Colors.RED}{Colors.BOLD}⚠️  Permission Required{Colors.RESET}"
        )
        lines.append(f"    {Colors.WHITE}{reason}{Colors.RESET}")
    
    elif event_type == 'DISPLAY_UPDATE':
        text = data.get('text', '')
        mode = data.get('mode', '')
        lines.append(
            f"  {Colors.BRIGHT_CYAN}📺 Display Update{Colors.RESET}"
        )
        if text:
            lines.append(f"    {Colors.WHITE}{text[:60]}{Colors.RESET}")
        if mode:
            lines.append(f"    {Colors.DIM}[{mode}]{Colors.RESET}")
    
    elif event_type == 'BATTERY_UPDATE':
        level = data.get('level', 0)
        color = Colors.GREEN if level > 50 else Colors.YELLOW if level > 20 else Colors.RED
        lines.append(
            f"  {color}🔋 Battery: {level}%{Colors.RESET}"
        )
    
    elif event_type == 'CHARGING_START':
        lines.append(
            f"  {Colors.GREEN}🔌 Charging started{Colors.RESET}"
        )
    
    elif event_type == 'CHARGING_STOP':
        lines.append(
            f"  {Colors.YELLOW}🔌 Charging stopped{Colors.RESET}"
        )
    
    else:
        # Generic fallback
        lines.append(
            f"  {Colors.WHITE}{event_type}{Colors.RESET}"
        )
        if data:
            lines.append(f"    {Colors.DIM}{str(data)[:80]}{Colors.RESET}")
    
    return '\n'.join(lines)


def format_state(state):
    """Format device state for display."""
    lines = []
    lines.append(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════╗{Colors.RESET}")
    lines.append(f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.BOLD}Device State{Colors.RESET}                          {Colors.CYAN}║{Colors.RESET}")
    lines.append(f"{Colors.BOLD}{Colors.CYAN}╠══════════════════════════════════════════╣{Colors.RESET}")
    
    # Display mode
    mode = state.get('display_mode', 'UNKNOWN')
    mode_color = Colors.GREEN if mode == 'IDLE' else Colors.YELLOW
    lines.append(
        f"{Colors.CYAN}║{Colors.RESET}  Mode: {mode_color}{mode:27}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}"
    )
    
    # Display text (truncated)
    text = state.get('display_text', '')[:25]
    if text:
        lines.append(
            f"{Colors.CYAN}║{Colors.RESET}  Text: {Colors.WHITE}{text:27}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}"
        )
    
    # Battery
    battery = state.get('battery_level', 0)
    battery_color = Colors.GREEN if battery > 50 else Colors.YELLOW if battery > 20 else Colors.RED
    lines.append(
        f"{Colors.CYAN}║{Colors.RESET}  Battery: {battery_color}{battery}%{Colors.RESET}{' ' * (25 - len(str(battery)))} {Colors.CYAN}║{Colors.RESET}"
    )
    
    # Connection status
    connected = state.get('connected', False)
    conn_str = f"{Colors.GREEN}Connected{Colors.RESET}" if connected else f"{Colors.RED}Disconnected{Colors.RESET}"
    padding = 27 - (len('Connected') if connected else len('Disconnected'))
    lines.append(
        f"{Colors.CYAN}║{Colors.RESET}  Status: {conn_str}{' ' * padding} {Colors.CYAN}║{Colors.RESET}"
    )
    
    # Last update
    last_update = state.get('last_update', '')
    if last_update:
        time_str = format_timestamp(last_update)
        lines.append(
            f"{Colors.CYAN}║{Colors.RESET}  Updated: {Colors.DIM}{time_str:25}{Colors.RESET} {Colors.CYAN}║{Colors.RESET}"
        )
    
    lines.append(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════╝{Colors.RESET}\n")
    
    return '\n'.join(lines)


async def test_connection():
    """Test WebSocket connection to dashboard server."""
    url = "ws://localhost:8080/ws"
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║{Colors.RESET}  {Colors.BOLD}Pager Feed WebSocket Test{Colors.RESET}            {Colors.CYAN}║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════╝{Colors.RESET}\n")
    
    print(f"{Colors.DIM}Connecting to: {url}{Colors.RESET}")
    
    try:
        async with websockets.connect(url) as ws:
            print(f"{Colors.GREEN}✓ Connected!{Colors.RESET}\n")
            print(f"{Colors.DIM}Listening for events... (Ctrl+C to exit){Colors.RESET}\n")
            print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}\n")
            
            message_count = 0
            
            async for message in ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'state':
                        # Device state update
                        state = data.get('data', {})
                        print(format_state(state))
                    
                    elif msg_type == 'event':
                        # Live event
                        event = data.get('data', {})
                        print(format_event(event))
                        print(f"\n{Colors.DIM}{'─' * 50}{Colors.RESET}\n")
                        
                        message_count += 1
                    
                    elif msg_type == 'build_status':
                        # Build status
                        status = data.get('status', '')
                        duration = data.get('duration_s', 0)
                        
                        if status == 'compiling':
                            print(f"  {Colors.YELLOW}⚙️  Compiling firmware...{Colors.RESET}\n")
                        elif status == 'uploading':
                            print(f"  {Colors.BLUE}📤 Uploading firmware...{Colors.RESET}\n")
                        elif status == 'done':
                            print(f"  {Colors.GREEN}✓ Build completed ({duration:.1f}s){Colors.RESET}\n")
                        elif status == 'failed':
                            print(f"  {Colors.RED}✗ Build failed ({duration:.1f}s){Colors.RESET}\n")
                        
                        print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}\n")
                    
                    else:
                        # Unknown message type
                        print(f"  {Colors.DIM}Unknown message type: {msg_type}{Colors.RESET}\n")
                
                except json.JSONDecodeError:
                    print(f"{Colors.RED}✗ Invalid JSON received{Colors.RESET}\n")
                except Exception as e:
                    print(f"{Colors.RED}✗ Error processing message: {e}{Colors.RESET}\n")
    
    except ConnectionRefusedError:
        print(f"{Colors.RED}✗ Connection refused!{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Troubleshooting:{Colors.RESET}")
        print(f"  1. Check if dashboard server is running:")
        print(f"     {Colors.DIM}sudo systemctl status clawd-dashboard{Colors.RESET}")
        print(f"  2. Or start it manually:")
        print(f"     {Colors.DIM}cd ~/clawd/work/clawd-pager && python -m devtools.dashboard_server{Colors.RESET}")
        print(f"  3. Verify port 8080 is listening:")
        print(f"     {Colors.DIM}netstat -tln | grep 8080{Colors.RESET}")
        sys.exit(1)
    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"{Colors.RED}✗ Invalid status code: {e}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}The WebSocket endpoint might not be configured.{Colors.RESET}")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.DIM}Interrupted by user{Colors.RESET}")
        sys.exit(0)
    
    except Exception as e:
        print(f"{Colors.RED}✗ Unexpected error: {e}{Colors.RESET}")
        sys.exit(1)


def print_test_commands():
    """Print commands to trigger test events."""
    print(f"\n{Colors.BOLD}Test Commands{Colors.RESET}")
    print(f"{Colors.DIM}Run these in another terminal to trigger events:{Colors.RESET}\n")
    
    commands = [
        ("Tool start (Edit)", 
         'curl -X POST http://localhost:8081/agent -H "Content-Type: application/json" '
         '-d \'{"event_type":"TOOL_START","tool":"Edit","display_text":"dashboard.py","display_sub":"+10 -3"}\''),
        
        ("Tool start (Bash)",
         'curl -X POST http://localhost:8081/agent -H "Content-Type: application/json" '
         '-d \'{"event_type":"TOOL_START","tool":"Bash","display_text":"ls -la"}\''),
        
        ("Agent waiting",
         'curl -X POST http://localhost:8081/agent -H "Content-Type: application/json" '
         '-d \'{"event_type":"WAITING"}\''),
        
        ("Question",
         'curl -X POST http://localhost:8081/agent -H "Content-Type: application/json" '
         '-d \'{"event_type":"QUESTION","question":"Should I proceed?"}\''),
    ]
    
    for label, cmd in commands:
        print(f"{Colors.CYAN}# {label}{Colors.RESET}")
        print(f"{Colors.DIM}{cmd}{Colors.RESET}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Pager Feed WebSocket')
    parser.add_argument('--show-commands', action='store_true',
                       help='Show test commands and exit')
    args = parser.parse_args()
    
    if args.show_commands:
        print_test_commands()
        sys.exit(0)
    
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        print(f"\n{Colors.DIM}Exiting...{Colors.RESET}")
