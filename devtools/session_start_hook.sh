#!/usr/bin/env bash
# Clawd Pager — SessionStart hook for Claude Code
#
# Checks if the local bridge is running, starts it if not, and reports
# pager/toolchain status. Never blocks session start on failure.
#
# Hook config (.claude/settings.local.json):
#   "SessionStart": [{ "matcher": "", "hooks": [{
#     "type": "command",
#     "command": "/path/to/clawd-pager/devtools/session_start_hook.sh",
#     "timeout": 15
#   }]}]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SCRIPT="$SCRIPT_DIR/local_bridge.py"
BRIDGE_HOST="${BRIDGE_HOST:-127.0.0.1}"
BRIDGE_PORT="${BRIDGE_PORT:-8081}"
BRIDGE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"
PAGER_IP="${PAGER_IP:-192.168.50.85}"
BRIDGE_LOG="/tmp/clawd_bridge.log"
BRIDGE_PID_FILE="/tmp/clawd_bridge.pid"

# --- Helpers ----------------------------------------------------------------

check_bridge_health() {
    # Returns 0 if bridge responds OK, 1 otherwise
    local resp
    resp=$(curl -sf --max-time 2 "${BRIDGE_URL}/health" 2>/dev/null) || return 1
    echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='ok' else 1)" 2>/dev/null
}

get_pager_status() {
    # Returns pager connected status from /health
    local resp
    resp=$(curl -sf --max-time 2 "${BRIDGE_URL}/health" 2>/dev/null) || { echo "unknown"; return; }
    echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print('connected' if d.get('pager') else 'disconnected')" 2>/dev/null || echo "unknown"
}

start_bridge() {
    # Start local_bridge.py as a fully detached background process
    if [ ! -f "$BRIDGE_SCRIPT" ]; then
        echo "Bridge script not found: $BRIDGE_SCRIPT" >&2
        return 1
    fi

    # Check if python3 has required deps
    if ! python3 -c "import aiohttp, aioesphomeapi" 2>/dev/null; then
        echo "Missing Python deps (aiohttp, aioesphomeapi). Run: pip install aiohttp aioesphomeapi" >&2
        return 1
    fi

    # Kill stale bridge if PID file exists but process is dead
    if [ -f "$BRIDGE_PID_FILE" ]; then
        local old_pid
        old_pid=$(cat "$BRIDGE_PID_FILE" 2>/dev/null)
        if [ -n "$old_pid" ] && ! kill -0 "$old_pid" 2>/dev/null; then
            rm -f "$BRIDGE_PID_FILE"
        fi
    fi

    # Launch detached: nohup + redirect + disown
    PAGER_IP="$PAGER_IP" nohup python3 "$BRIDGE_SCRIPT" --pager-ip "$PAGER_IP" --port "$BRIDGE_PORT" \
        > "$BRIDGE_LOG" 2>&1 &
    local pid=$!
    echo "$pid" > "$BRIDGE_PID_FILE"
    disown "$pid" 2>/dev/null || true

    return 0
}

# --- Main -------------------------------------------------------------------

STATUS_LINES=()

# 1. Check if bridge is already running
if check_bridge_health; then
    pager_status=$(get_pager_status)
    if [ "$pager_status" = "connected" ]; then
        STATUS_LINES+=("🦞 Pager bridge running — pager connected")
    else
        STATUS_LINES+=("⚠️  Pager bridge running — pager offline (${PAGER_IP})")
    fi
else
    # Bridge not running — try to start it
    STATUS_LINES+=("Starting pager bridge...")
    if start_bridge; then
        # Wait for it to come up
        sleep 3
        if check_bridge_health; then
            pager_status=$(get_pager_status)
            if [ "$pager_status" = "connected" ]; then
                STATUS_LINES+=("🦞 Pager bridge started — pager connected")
            else
                STATUS_LINES+=("⚠️  Pager bridge started — pager offline (${PAGER_IP})")
            fi
        else
            STATUS_LINES+=("❌ Pager bridge failed to start (check ${BRIDGE_LOG})")
        fi
    else
        STATUS_LINES+=("❌ Pager bridge could not be launched")
    fi
fi

# 2. Secondary tool checks (non-blocking, informational only)

# ESPHome check
if command -v esphome &>/dev/null; then
    esphome_ver=$(esphome version 2>/dev/null | head -1 || echo "unknown")
    STATUS_LINES+=("  ESPHome: ${esphome_ver}")
elif [ -f "${HOME}/clawd/esphome-env/bin/esphome" ]; then
    STATUS_LINES+=("  ESPHome: available (activate venv)")
else
    STATUS_LINES+=("  ESPHome: not found")
fi

# ESP-IDF check
if [ -n "${IDF_PATH:-}" ]; then
    idf_ver=$(python3 -c "import re; v=open('${IDF_PATH}/version.txt').read().strip(); print(v)" 2>/dev/null || echo "installed")
    STATUS_LINES+=("  ESP-IDF: v${idf_ver}")
elif [ -d "${HOME}/esp/esp-idf" ]; then
    STATUS_LINES+=("  ESP-IDF: available (source export.sh)")
else
    STATUS_LINES+=("  ESP-IDF: not found")
fi

# USB device check (for flashing)
if ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1 >/dev/null 2>&1; then
    devices=$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
    STATUS_LINES+=("  USB: ${devices}")
else
    STATUS_LINES+=("  USB: no devices")
fi

# 3. Output status as JSON for Claude Code hook response
# The additionalContext field shows up in Claude's context
output=""
for line in "${STATUS_LINES[@]}"; do
    if [ -n "$output" ]; then
        output="${output}\n${line}"
    else
        output="$line"
    fi
done

# Print as JSON to stdout (Claude Code hook protocol)
python3 -c "
import json, sys
msg = '''$(printf '%s' "$output")'''
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': msg
    }
}))
"

exit 0
