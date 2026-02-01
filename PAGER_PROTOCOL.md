# Pager Protocol - When Claude MUST Ask

This document establishes clear rules for when Claude must ask permission via the pager, even though tools are auto-approved.

## Core Principle

**Auto-approved permissions are for speed, NOT for autonomy.** Just because I *can* run a tool doesn't mean I *should* without asking.

## MUST Ask Via Pager (Always)

### 1. Code Changes
- **Any Edit or Write to firmware** (`clawd-pager.yaml`)
  - Question: "Fix [bug/add feature]? May need recompile."
  - Wait for YES before proceeding

- **Bridge changes** (`bridge.py`)
  - Question: "Update bridge code? Will restart service."
  - Wait for YES before proceeding

- **Hook changes** (`claude_hook.py`, `settings.local.json`)
  - Question: "Modify hooks/permissions?"
  - Wait for YES before proceeding

### 2. Deployment Operations
- **Firmware compile + upload**
  - Question: "Compile & upload firmware? Takes ~40s."
  - Wait for YES before proceeding

- **Bridge restart**
  - Question: "Restart bridge? Pager will disconnect briefly."
  - Wait for YES before proceeding

### 3. Potentially Disruptive Actions
- **Installing new dependencies**
  - Question: "Install [package]?"
  - Wait for YES before proceeding

- **Creating new files** (except logs/temp files)
  - Question: "Create new file [name]?"
  - Wait for YES before proceeding

- **Deleting files**
  - ALWAYS ask, even for obvious junk
  - Question: "Delete [file]?"
  - Wait for YES before proceeding

### 4. Experimental Features
- **Trying something new**
  - Question: "Try [experimental approach]? May not work."
  - Wait for YES before proceeding

- **Deviating from plan**
  - Question: "Found better approach: [description]. Switch?"
  - Wait for YES before proceeding

## CAN Proceed Without Asking (Auto-Execute)

### Safe Operations
- ✅ Read files
- ✅ Grep/Glob searches
- ✅ Git status, diff, log (read-only)
- ✅ Journalctl logs
- ✅ TodoWrite updates
- ✅ Web searches
- ✅ Documentation reads

### Planned Work
- ✅ Following explicit user instructions
  - User: "Fix the button bug" → Fix it (ask about approach if unclear)
  - User: "Add feature X" → Add it (ask before compile/upload)

### Non-Critical Edits
- ✅ Documentation updates (README, comments, AUDIT.md)
- ✅ Adding to backlog/todo lists
- ✅ Fixing obvious typos in comments (not code!)

## The Ask Format

When asking via pager, use this format:

```python
response = Bash: python3 /home/monroe/clawd/work/clawd-pager/devtools/claude_hook.py ask "BRIEF QUESTION?" --timeout 60
```

**Question Guidelines:**
- ✅ "Fix button bug? Needs recompile."
- ✅ "Upload firmware? Takes 40s."
- ✅ "Add blinking eyes animation?"
- ❌ "Should I modify the clawd-pager.yaml file located at /home/monroe/... by editing lines 123-456 to change the button handler logic?" (TOO LONG)

**Keep questions:**
- Under 50 characters if possible
- Action-focused (Fix/Add/Upload/Delete)
- Include consequence (recompile/restart/etc)

## Timeout Handling

```python
response = ask_via_pager("Question?", timeout=60)

if response == "yes":
    # Proceed
elif response == "no":
    # Explain why I wanted to do it, ask for alternative
else:
    # Timeout - assume NO, ask again or wait for user to return
```

## Exception: Emergencies

If the pager itself is broken or the bridge is down, fall back to regular Claude Code permission prompts. Mention in response: "Note: Pager unavailable, using keyboard prompts."

## Accountability

Every time I ask via pager:
- Log to dashboard: `CLAUDE_ASKED: "question text"`
- Log response: `USER_RESPONSE: yes/no/timeout`
- Reviewable in event log for audit trail

## Examples

### ✅ GOOD - Asked First
```
User: "The button handler has a bug"
Me: *asks via pager* "Fix button bug? Needs recompile."
Pager: Shows question
User: *Button A*
Me: "Great!" *edits code, compiles, uploads*
```

### ❌ BAD - Didn't Ask
```
User: "The button handler has a bug"
Me: *immediately edits code, compiles, uploads*
User: "WTF I was testing something!"
```

### ✅ GOOD - Explained Approach First
```
User: "Add a feature to show notifications"
Me: *sends to pager* "Show notifications as popup? OR add to history?"
User: *Button A for popup*
Me: "Popup it is!" *asks again* "Ready to code this?"
User: *Button A*
Me: *codes, asks before upload*
```

## Trust, But Verify

This protocol exists because:
1. **You trusted me** with auto-approve permissions
2. **I respect that trust** by asking before significant actions
3. **The pager enables** seamless remote approval
4. **We both benefit** from faster iteration without keyboard interrupts

If I violate this protocol (act without asking when I should have), call me out immediately. The protocol gets updated and I learn.

## Version

- **v1.0** - Initial protocol (2026-01-31)
- Changes to this protocol require user approval via pager: "Update pager protocol?"
