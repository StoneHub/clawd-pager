# Clawd Pager - Code Audit Report

**Original**: 2026-01-31 (Claude Opus 4.5)
**Updated**: 2026-02-06 (Claude Opus 4.6)

---

## Executive Summary

**Status**: FUNCTIONAL — button conflicts resolved, mode naming fixed, C++ refactoring unblocked.

The Jan 31 audit identified button handler conflicts between firmware and bridge caused by mid-session layout changes. Those changes were subsequently committed (commits `9a8e7b1` through `5d6f109`), resolving the firmware-side conflicts. A separate issue — display mode name mismatch between hook and firmware — was found and fixed on Feb 6.

---

## What Changed Since Original Audit

### Resolved Issues

1. **Button handler conflicts** — The "new ergonomic layout" (A=Yes/Voice/Status, B=No/Back) was committed across multiple subsequent patches. The firmware YAML now has a self-consistent button layout.

2. **DisplayModeManager routing** — The 10-line TODO in `display_mode_manager.h` has been implemented. The manager routes LISTENING, PROCESSING, and AGENT modes to C++ classes, returns `false` for all other modes so YAML handles them.

3. **Display mode name mismatch (NEW)** — The hook (`claude_hook.py`) was sending mode names like `EDIT`, `BASH`, `READ`, `SEARCH`, `WEB`, `PLANNING` that didn't match the firmware's `AGENT_EDIT`, `AGENT_BASH`, `AGENT_READ`, `AGENT_SEARCH`, `AGENT_WEB`, `AGENT_PLAN`. This meant tool-specific display modes were falling through to the generic RESPONSE renderer. Fixed: all hook modes now use `AGENT_*` prefix to match firmware.

4. **Watcher submodule** — Re-initialized at latest upstream HEAD (the fork commit `ffb56b8` with the Tamagotchi example no longer exists upstream). The Pocket Tamagotchi example would need to be recreated.

### Remaining Issues

1. **Bridge alignment** — `bridge.py` lives on the Pi (`/home/monroe/clawd/scripts/`) and is not in this repo. It may also need its mode name mapping updated to match the `AGENT_*` convention. Check whether the bridge transforms mode names or passes them through.

2. **C++ mode integration** — The DisplayModeManager is complete but not yet wired into the YAML display lambda. The YAML still has all modes inline. To activate:
   ```yaml
   # In display lambda, before the existing mode checks:
   if (DisplayModeManager::render(it, mode, msg)) return;
   ```
   This requires a compile+upload cycle to verify.

3. **Voice capture end-to-end** — Never tested. Button A hold triggers recording in firmware, but the bridge button handler may still expect Button B for voice (per the original audit's bridge analysis).

4. **Response routing** — Button responses (YES/NO in QUESTION/PERMISSION modes) update firmware state (`PERM_APPROVED`/`PERM_DENIED`) which the bridge detects. This path works for permissions but the general QUESTION->response->agent flow is untested.

---

## Current Button Layout (Firmware)

### Button A (GPIO37, top)
| Context | Short Tap | Long Hold (400ms+) |
|---------|-----------|---------------------|
| IDLE/DOCKED | Get status | Voice recording |
| QUESTION | YES (Zelda sound) | Voice recording |
| PERMISSION | APPROVED | Voice recording |
| CONFIRM | SEND | Voice recording |

### Button B (GPIO39, front)
| Context | Short Tap |
|---------|-----------|
| QUESTION | NO (sad trombone) |
| PERMISSION | DENIED (warning buzz) |
| CONFIRM | CANCEL |
| Other (not IDLE) | BACK to IDLE |

---

## Display Mode Inventory

### Hook -> Firmware Mode Mapping (After Fix)

| Tool | Hook sends | Firmware mode | Firmware handler |
|------|-----------|---------------|------------------|
| Edit | `AGENT_EDIT` | `AGENT_EDIT` | Filename, +/- lines, code preview |
| Write | `AGENT_NEW` | `AGENT_NEW` | Sparkle effect, file icon |
| Read | `AGENT_READ` | `AGENT_READ` | Blue header, scrolling pages |
| Bash | `AGENT_BASH` | `AGENT_BASH` | Terminal style, command preview |
| Grep/Glob | `AGENT_SEARCH` | `AGENT_SEARCH` | Purple, magnifying glass |
| WebSearch/Fetch | `AGENT_WEB` | `AGENT_WEB` | Cyan globe animation |
| Task | `AGENT_SUB` | `AGENT_SUB` | Pink, sub-agent type |
| TodoWrite | `AGENT_PLAN` | `AGENT_PLAN` | Amber, todo items |
| AskUserQuestion | `QUESTION` | `QUESTION` | Amber flash, A=YES prompt |
| Generic/unknown | `AGENT` | `AGENT` | Matrix code rain |

### Internal Firmware Modes (Not from hook)

| Mode | Trigger | Description |
|------|---------|-------------|
| `IDLE` | Default/boot | Static clock, battery, date |
| `DOCKED` | Charging detected | Ambient particles, clock |
| `LISTENING` | Button A hold | Rainbow waveform |
| `PROCESSING` | After voice/action | Bouncing dots |
| `CONFIRM` | After voice transcription | Show text, A=Send B=Cancel |
| `PERMISSION` | PreToolUse hook | Red/orange flash, A=YES B=NO |
| `PERM_APPROVED` | Button A in PERMISSION | Bridge detects this state |
| `PERM_DENIED` | Button B in PERMISSION | Bridge detects this state |
| `BRIEFING` | Status fetch response | Teal header, A=More B=Done |
| `LOADING` | Fetching data | Minimal dots |
| `ALERT` | Alert service | Red flash header |
| `AWAITING` | Waiting for response | Purple pulse circles |
| `RESPONSE` | Default fallthrough | Coral accent, text display |

---

## Lessons Learned

1. **One change -> compile -> test -> commit.** The Jan 31 session's ~30% token waste came from making multiple untested cross-component changes.

2. **Mode names must be consistent across the stack.** The hook->bridge->firmware pipeline is only as good as its string contracts. Document the mode name mapping (done above).

3. **Bridge code should be in the repo.** Having `bridge.py` only on the Pi makes it impossible to audit the full stack in one place.

---

## Next Steps (Priority Order)

1. **Verify bridge mode mapping** — SSH to fcfdev, check if `bridge.py` transforms mode names or passes through
2. **Wire DisplayModeManager into YAML** — Add the one-line guard, compile, test
3. **Test voice pipeline** — Hold A, speak, verify bridge receives audio
4. **Test permission flow** — Trigger a dangerous command, verify pager shows prompt, buttons work
5. **Recreate Pocket Tamagotchi** — The example was lost when the fork commit disappeared; recreate from CLAUDE.md docs

---

*Updated for external review. All source files in repository.*
