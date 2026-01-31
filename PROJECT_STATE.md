# Clawd Pager - Project State

**Last Updated**: 2026-01-31 17:30 EST

## [V4.1] AGENT Mode + Systemd Services (IN PROGRESS)

### New Features:
- **DOCKED mode** - Ambient animation when charging (battery < 99%)
- **AGENT mode** - Matrix code rain when Claude Code is working
- **Claude Code hooks** - PreToolUse/PostToolUse emit events to pager
- **Bridge API** - Port 8081 receives agent events
- **Systemd services** - Auto-start on boot (pending install)

### Files Created:
- `devtools/claude_hook.py` - Hook script for Claude Code
- `devtools/clawd-dashboard.service` - Systemd service
- `devtools/clawd-bridge.service` - Systemd service  
- `devtools/clawd-sudoers` - Passwordless service management

### To Install Services:
```bash
sudo cp devtools/clawd-*.service /etc/systemd/system/
sudo cp devtools/clawd-sudoers /etc/sudoers.d/clawd
sudo chmod 440 /etc/sudoers.d/clawd
sudo systemctl daemon-reload
sudo systemctl enable --now clawd-dashboard clawd-bridge
```

### Quick Test:
```bash
# Test hook manually
python3 devtools/claude_hook.py TOOL_START "Edit"
python3 devtools/claude_hook.py TOOL_END "Edit"
```

## Config
- Device: 192.168.50.85
- Dashboard: :8080
- Bridge API: :8081
- ESPHome: 2024.12.4 (DO NOT UPGRADE)
