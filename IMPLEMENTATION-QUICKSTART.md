# Pager Feed Integration - Quick Start Guide

**Goal:** Add live Claude Code activity feed to screensaver dashboard  
**Time Required:** 30 minutes  
**Difficulty:** Easy (copy-paste integration)

---

## What You're Getting

The screensaver will display:
- ✅ Real-time Claude Code tool activity (Edit, Read, Bash, etc.)
- ✅ File names and line diffs for edits
- ✅ Voice command transcripts
- ✅ Button presses from pagers
- ✅ Questions from Claude Code
- ✅ Pager connection status
- ✅ Last 5 events with timestamps

**Architecture:** WebSocket subscription to existing dashboard_server.py (port 8080)  
**CPU Impact:** <2% average (brief spikes during events)  
**Network:** Local only (ws://localhost:8080/ws)

---

## Prerequisites Check

```bash
# 1. Verify dashboard server is running
sudo systemctl status clawd-dashboard
# OR
ps aux | grep dashboard_server

# 2. Verify bridge is running
ps aux | grep bridge.py

# 3. Check listening ports
netstat -tln | grep -E "(8080|8081)"
# Should show:
# 0.0.0.0:8080 (dashboard server)
# 0.0.0.0:8081 (bridge API)

# 4. Test WebSocket endpoint
curl http://localhost:8080/api/state
# Should return JSON with device state
```

If any services are missing, start them:
```bash
# Start dashboard server
cd ~/clawd/work/clawd-pager
python -m devtools.dashboard_server &

# Start bridge (if not running)
cd ~/clawd/scripts
python bridge.py &
```

---

## Installation Steps

### Step 1: Install Dependencies (1 minute)

```bash
pip3 install websockets
```

### Step 2: Test WebSocket Connection (2 minutes)

```bash
# Run the test script
cd ~/clawd/work/clawd-pager
./test-pager-feed.py

# You should see:
# ✓ Connected!
# Listening for events...
# [Device state display]

# In another terminal, trigger a test event:
curl -X POST http://localhost:8081/agent \
  -H "Content-Type: application/json" \
  -d '{"event_type":"TOOL_START","tool":"Edit","display_text":"test.py","display_sub":"+5 -2"}'

# The test script should immediately show the event!
# Press Ctrl+C to exit when satisfied.
```

If the test works, proceed to Step 3. If not, see Troubleshooting section below.

### Step 3: Integrate Into Screensaver (10 minutes)

Open the screensaver dashboard file:
```bash
cd ~/clawd/screensaver-dashboard
# Backup first
cp dashboard.py dashboard-backup.py
# Edit
nano dashboard.py  # or your preferred editor
```

**Make these changes** (refer to `screensaver-integration-patch.py` for full code):

#### A. Add imports (at top, after existing imports)
```python
import websockets
import asyncio
from threading import Thread
```

#### B. Copy the `PagerFeedClient` class
Copy the entire `PagerFeedClient` class from `screensaver-integration-patch.py` and paste it **before** the `InformationDashboard` class.

#### C. Initialize in `__init__` (after `self.show_all()`)
```python
# In InformationDashboard.__init__, add after self.show_all():

# Pager activity tracking
self.pager_activity = []
self.max_activity_items = 5
self.pager_connected = False

# Start pager feed
self.pager_feed = PagerFeedClient(self.on_pager_event)
self.pager_feed.start()
```

#### D. Add event handler method
Copy the `on_pager_event` method from `screensaver-integration-patch.py` into the `InformationDashboard` class.

#### E. Replace `update_clawdbot` method
Replace the existing `update_clawdbot()` method with the enhanced version from `screensaver-integration-patch.py`.

**Full example:**
```bash
# See screensaver-integration-patch.py for complete code
cat ~/clawd/work/clawd-pager/screensaver-integration-patch.py
```

### Step 4: Test the Screensaver (5 minutes)

```bash
# Launch screensaver
cd ~/clawd/screensaver-dashboard
./dashboard.py

# You should see in terminal:
# 🚀 Pager feed client started
# 🔌 Connecting to pager feed: ws://localhost:8080/ws
# ✅ Pager feed connected

# The "Pagers & Gateway" panel should show:
# ● Feed Connected

# Trigger a Claude Code event (in another terminal):
claude code
# (use a tool like Edit, Read, etc.)

# The screensaver should update within 1 second with the event!
```

---

## Testing Checklist

- [ ] WebSocket test script connects successfully
- [ ] Test events appear in test script
- [ ] Screensaver shows "● Feed Connected"
- [ ] Claude Code tool use appears in screensaver
- [ ] Events have timestamps (HH:MM:SS)
- [ ] Old events are removed (keeps last 5)
- [ ] CPU usage stays <5% (check with `top`)
- [ ] Auto-reconnects if dashboard server restarts
- [ ] No GTK errors or crashes

---

## Troubleshooting

### "Connection refused" Error

**Cause:** Dashboard server not running  
**Fix:**
```bash
# Check status
sudo systemctl status clawd-dashboard

# If not running, start it
cd ~/clawd/work/clawd-pager
python -m devtools.dashboard_server &

# Or with systemd
sudo systemctl start clawd-dashboard
```

### "No events showing"

**Cause:** Bridge not running or not configured  
**Fix:**
```bash
# Check bridge is running
pgrep -f bridge.py

# If not, start it
cd ~/clawd/scripts
python bridge.py &

# Or with systemd
sudo systemctl restart clawdbot-pager

# Verify bridge API is responding
curl http://localhost:8081/status
```

### "Feed offline" message

**Cause:** Dashboard server WebSocket not available  
**Fix:**
```bash
# Check if port 8080 is listening
netstat -tln | grep 8080

# Test WebSocket endpoint
curl http://localhost:8080/api/state

# Check dashboard server logs
journalctl -u clawd-dashboard -f
```

### High CPU usage

**Cause:** Too many events or inefficient rendering  
**Fix:**
```bash
# Check CPU usage
top -p $(pgrep -f dashboard.py)

# If sustained >10%, check:
# 1. Are events flooding in? (check bridge logs)
# 2. Is max_activity_items set correctly? (should be 5)
# 3. Is GTK updating too frequently?

# Adjust max_activity_items in dashboard.py:
self.max_activity_items = 3  # Reduce from 5
```

### Events delayed

**Cause:** Network latency or event processing backlog  
**Fix:**
```bash
# Check network latency
ping localhost

# Check if dashboard server is busy
top -p $(pgrep -f dashboard_server)

# Check event queue size
curl http://localhost:8080/api/events/recent?limit=1
```

---

## Advanced Configuration

### Adjust Event Display Count

```python
# In InformationDashboard.__init__:
self.max_activity_items = 3  # Show only 3 events instead of 5
```

### Filter Specific Event Types

```python
# In on_pager_event method, modify filter:
if event_type in [
    'TOOL_START',  # Show these
    'WAITING',
    'QUESTION'
    # Remove others to filter them out
]:
```

### Change Reconnect Delay

```python
# In PagerFeedClient class:
self.reconnect_delay = 10  # Wait 10 seconds instead of 5
```

### Disable Auto-Reconnect

```python
# In PagerFeedClient.connect method, remove the while loop:
async def connect(self):
    # Remove: while self.running:
    try:
        async with websockets.connect(self.ws_url) as ws:
            # ... rest of code
```

---

## Performance Tips

1. **Keep max_activity_items low** (5 or less)
   - Each event adds ~20 lines of markup
   - GTK rendering scales with content

2. **Truncate long strings**
   - File paths: `file[:30]`
   - Tool text: `text[:40]`
   - This keeps rendering fast

3. **Use `GLib.idle_add` for thread safety**
   - Already implemented in patch
   - Don't call GTK from background thread directly

4. **Avoid polling**
   - WebSocket push model is efficient
   - No need to add timers for event checks

---

## Next Steps

Once working:

1. **Add more event types**
   - Check `event_logger.py` for full list
   - Add cases to `on_pager_event` and `update_clawdbot`

2. **Enhance display**
   - Add emoji icons (📝, 📖, 💻, etc.)
   - Color-code by tool type
   - Show code snippets for small edits

3. **Add animations** (optional)
   - Pulsing activity indicator
   - Fade-in new events
   - Scroll long event lists

4. **Create session replay** (future)
   - Load historical session from dashboard server
   - Replay events with timing
   - Useful for debugging and demos

---

## File Reference

| File | Purpose |
|------|---------|
| `PAGER-FEED-INTEGRATION.md` | Full architecture documentation (25KB) |
| `screensaver-integration-patch.py` | Copy-paste code for dashboard.py (16KB) |
| `test-pager-feed.py` | WebSocket connection test script (14KB) |
| `IMPLEMENTATION-QUICKSTART.md` | This file - quick start guide |

---

## Quick Commands Reference

```bash
# Test WebSocket
./test-pager-feed.py

# Test with manual event
curl -X POST http://localhost:8081/agent \
  -H "Content-Type: application/json" \
  -d '{"event_type":"TOOL_START","tool":"Edit","display_text":"test.py"}'

# Check services
sudo systemctl status clawd-dashboard
sudo systemctl status clawdbot-pager

# Check CPU usage
top -p $(pgrep -f dashboard.py)

# View logs
journalctl -u clawd-dashboard -f
journalctl -u clawdbot-pager -f

# Restart services
sudo systemctl restart clawd-dashboard
sudo systemctl restart clawdbot-pager
```

---

## Success!

If you see events appearing in the screensaver panel within 1 second of Claude Code activity, **you're done!** 🎉

The screensaver now has:
- ✅ Live activity feed
- ✅ Real-time updates
- ✅ Low CPU usage (<2%)
- ✅ Auto-reconnect
- ✅ Graceful fallback

**Total integration time:** ~30 minutes  
**Lines of code added:** ~150  
**New services needed:** 0  

---

## Questions?

Check the full documentation in `PAGER-FEED-INTEGRATION.md` for:
- Detailed architecture diagrams
- Event format specifications
- Alternative approaches considered
- Future enhancement ideas
- Complete API reference

---

**Happy coding!** 🦞📟✨
