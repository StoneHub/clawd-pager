# Quick Testing Commands

## Test the dashboard server

### Check server status
```bash
ps aux | grep dashboard_server | grep -v grep
lsof -i :8080
```

### View server logs
```bash
tail -f /tmp/dashboard_final.log
```

### Test API endpoints

#### Get summaries
```bash
curl -s http://localhost:8080/api/summaries | python3 -m json.tool
```

#### Get device state
```bash
curl -s http://localhost:8080/api/state | python3 -m json.tool
```

#### Send test event
```bash
curl -X POST http://localhost:8080/api/log \
  -H "Content-Type: application/json" \
  -d '{"source":"user","event_type":"TOOL_START","data":{"tool":"test","command":"test command"}}'
```

#### Test input validation

**Invalid JSON:**
```bash
curl -X POST http://localhost:8080/api/log \
  -H "Content-Type: application/json" \
  -d 'invalid json'
```

**Invalid event type:**
```bash
curl -X POST http://localhost:8080/api/log \
  -H "Content-Type: application/json" \
  -d '{"source":"user","event_type":"INVALID_TYPE","data":{}}'
```

**Data too large:**
```bash
LARGE_DATA=$(python3 -c 'print("x"*11000)')
curl -X POST http://localhost:8080/api/log \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"user\",\"event_type\":\"TOOL_START\",\"data\":{\"large\":\"$LARGE_DATA\"}}"
```

### Test batch summarization

**Send 10+ events to trigger summarization:**
```bash
for i in {1..12}; do
  curl -X POST http://localhost:8080/api/log \
    -H "Content-Type: application/json" \
    -d "{\"source\":\"user\",\"event_type\":\"AGENT_WORKING\",\"data\":{\"tool\":\"test\",\"status\":\"event_$i\"}}" \
    -s > /dev/null
  echo "Sent event $i"
done
```

### Test concurrent events (race condition test)
```bash
for i in {1..20}; do
  curl -X POST http://localhost:8080/api/log \
    -H "Content-Type: application/json" \
    -d "{\"source\":\"user\",\"event_type\":\"AGENT_WORKING\",\"data\":{\"tool\":\"concurrent\",\"status\":\"$i\"}}" \
    -s > /dev/null &
done
wait
echo "All concurrent events sent!"
```

### Check persistence
```bash
# View persisted summaries file
cat ~/.clawd/pager_summaries.json | python3 -m json.tool

# Restart server and check it loads summaries
# You should see "Loaded X summaries from disk" in the logs
```

## Restart the server

```bash
# Kill existing server
pkill -f dashboard_server

# Start server with API key
cd ~/clawd/work/clawd-pager
ANTHROPIC_API_KEY="your-key-here" \
  /home/monroe/clawd/esphome-env/bin/python -m devtools.dashboard_server
```
