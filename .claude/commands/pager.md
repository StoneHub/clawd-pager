---
description: Send alerts, messages, and questions to your M5StickC pager
arguments:
  - name: action
    description: "Action to perform: alert, say, ask, status, idle"
    required: false
  - name: message
    description: "Message to display on the pager"
    required: false
---

# Clawd Pager Control

Control and interact with the M5StickC Plus pager from Claude Code.

## Configuration
- **Bridge API**: http://192.168.50.50:8081
- **Dashboard**: http://192.168.50.50:8080
- **Device IP**: 192.168.50.85

## Commands

When the user runs `/pager`, ask what they want to do:

### Available Actions

1. **alert [message]** - Send an alert with distinct tone
2. **say [message]** - Display a message on the pager
3. **ask [question]** - Ask a yes/no question (Button A = Yes)
4. **status** - Show current pager state
5. **docked** - Enter ambient docked mode
6. **idle** - Return to home screen

## Implementation

Use `curl` to call the bridge API:

```bash
# Alert with tone
curl -X POST http://192.168.50.50:8081/device/alert \
  -H "Content-Type: application/json" \
  -d '{"text": "MESSAGE HERE"}'

# Display message (no tone)
curl -X POST http://192.168.50.50:8081/device/display \
  -H "Content-Type: application/json" \
  -d '{"text": "MESSAGE", "mode": "RESPONSE"}'

# Ask question (shows flashing "Press A = YES")
curl -X POST http://192.168.50.50:8081/device/display \
  -H "Content-Type: application/json" \
  -d '{"text": "Your question here?\n\n[A] = Yes", "mode": "QUESTION"}'

# Return to idle
curl -X POST http://192.168.50.50:8081/device/display \
  -H "Content-Type: application/json" \
  -d '{"text": "CLAWDBOT READY", "mode": "IDLE"}'
```

## Interactive Question Flow

When using "ask", the pager will show the question with a flashing "Press A = YES" button. The user can:
- Press **Button A** to answer "Yes"
- Press **Button B** to dismiss and return home

After asking a question, wait 10 seconds for a response, then check the dashboard for button events.

## Creative Ideas

- **Build notifications**: Alert when compile/upload finishes
- **Error alerts**: Flash red when tests fail
- **Progress updates**: Show what Claude is working on
- **Quick confirmations**: "Deploy to prod?" with Button A = Yes
- **Timer/reminders**: "Take a break!" after long sessions

## Examples

User: `/pager alert Build complete!`
Action: Send alert with distinct tone

User: `/pager ask Deploy to production?`
Action: Show question, wait for Button A press

User: `/pager say Working on auth module...`
Action: Display status message quietly
