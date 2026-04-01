# Activity Summarization Feature

## Overview

Added intelligent activity summarization to the Clawdbot Pager Bridge system for improved readability on small-screen displays.

## Quick Start

```bash
# Dashboard server starts automatically with summarization enabled
cd ~/clawd/work/clawd-pager
python3 -m devtools.dashboard_server

# Access summaries
curl http://localhost:8080/api/summaries

# Screensaver dashboard will automatically display summaries
python3 ~/clawd/screensaver-dashboard/dashboard.py
```

## How It Works

### Event Batching
- Dashboard server monitors incoming tool events (`TOOL_START`, `TOOL_END`, `AGENT_WORKING`, `AGENT_WAITING`)
- Events are batched until either:
  - **10 events** accumulated, OR
  - **5 minutes** elapsed since last batch

### Summarization
- When batch threshold met, calls Claude Haiku API to generate concise summary
- **Fallback mode**: If API unavailable, generates simple summary from event data
- Example summaries:
  - API mode: _"Fixed morning email rollup calendar integration"_
  - Fallback: _"Completed 10 operations using exec, read, write"_

### Storage
- Summaries stored in memory (rolling buffer)
- Maximum 20 summaries retained
- Each summary includes:
  ```json
  {
    "timestamp": "2026-02-11T15:43:09",
    "text": "Completed 10 operations using exec, read, write",
    "event_count": 10
  }
  ```

### Display
- Summaries available at `/api/summaries` REST endpoint
- Broadcast via WebSocket as type `summary`
- Screensaver dashboard fetches and displays automatically

## API Endpoints

### GET /api/summaries
Returns array of recent activity summaries.

**Response:**
```json
[
  {
    "timestamp": "2026-02-11T15:43:09",
    "text": "Completed 10 operations using exec, read, write, web_search, edit",
    "event_count": 10
  }
]
```

## Configuration

Edit `dashboard_server.py` to customize:

```python
self.max_summaries = 20           # Rolling buffer size
self.batch_size = 10               # Events per batch
self.batch_timeout_seconds = 300   # 5 minutes
```

## Dependencies

```bash
pip3 install --break-system-packages anthropic aiohttp
```

## Troubleshooting

### No summaries appearing
1. Check dashboard server is running: `ps aux | grep dashboard_server`
2. Verify events are being sent: `curl http://localhost:8080/api/events/recent`
3. Check for 10+ tool events in batch

### API errors
- Server will automatically fall back to simple summaries
- Check logs for API error details
- Verify `ANTHROPIC_API_KEY` in `.bashrc` if using Haiku API

### Screensaver not showing summaries
1. Verify API endpoint: `curl http://localhost:8080/api/summaries`
2. Check dashboard server is reachable
3. Restart screensaver dashboard

## Files Modified

- `devtools/dashboard_server.py` - Core summarization logic
- `~/clawd/screensaver-dashboard/dashboard.py` - Display integration

## Future Enhancements

- [ ] Persist summaries to disk for history beyond 20
- [ ] Add summary filtering by time range
- [ ] Support multi-bridge summary aggregation
- [ ] Add manual summary generation trigger
- [ ] Export summaries to markdown/PDF

## Testing

See `/tmp/pager-summarization-test-results.md` for comprehensive test results.

Quick test:
```bash
# Send 10 test events
for i in {1..5}; do
  curl -X POST http://localhost:8080/api/log \
    -H "Content-Type: application/json" \
    -d '{"source":"user","event_type":"TOOL_START","data":{"tool":"exec"}}' -s > /dev/null
  curl -X POST http://localhost:8080/api/log \
    -H "Content-Type: application/json" \
    -d '{"source":"user","event_type":"TOOL_END","data":{"tool":"exec","status":"success"}}' -s > /dev/null
done

# Check summary
curl -s http://localhost:8080/api/summaries | python3 -m json.tool
```

## Implementation Details

### Batch Timer
Automatic 5-minute timer triggers summarization even if batch size not reached.

### WebSocket Broadcast
New summaries are broadcast to all connected dashboards:
```json
{
  "type": "summary",
  "data": {
    "timestamp": "...",
    "text": "...",
    "event_count": 10
  }
}
```

### Rolling Buffer Logic
```python
self.summaries.insert(0, summary)  # Newest first
if len(self.summaries) > self.max_summaries:
    self.summaries = self.summaries[:self.max_summaries]
```

## Architecture

```
Tool Events → Bridge → POST /api/log → Dashboard Server
                                           ↓
                                    Event Batching
                                    (10 events or 5 min)
                                           ↓
                                    Summarize Batch
                                    (Haiku API / Fallback)
                                           ↓
                                    Store in Buffer (20 max)
                                           ↓
                                    WebSocket Broadcast
                                           ↓
                                    GET /api/summaries
                                           ↓
                                    Screensaver Dashboard
```

## Notes

- **Portable**: No external database required, all state in memory
- **Resilient**: Fallback mode ensures summaries always generated
- **Efficient**: Batching reduces API calls and improves readability
- **Self-contained**: Works across machines without shared dependencies

---

**Status**: ✅ Production Ready  
**Version**: 1.0  
**Date**: February 11, 2026
