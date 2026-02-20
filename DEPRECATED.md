# DEPRECATED: clawd-pager Relay Runtime

Status: Deprecated as primary relay runtime

## What this used to do

- Hosted dashboard/event tooling through `devtools/dashboard_server.py` on port `8080`.
- Worked with legacy `bridge.py` patterns to drive pager display workflows.
- Contained firmware and bridge integration docs for M5/ESPHome pagers.

## What supersedes it

- `/home/monroe/clawd/work/agent-relay/` is now the primary relay/control plane.
- Agent events are routed through provider drivers and notification adapters.

## What is still useful

- Firmware references and protocol documentation.
- Pager integration details used to keep ESPHome notifications compatible.

## Deactivation policy

- `clawd-dashboard.service` is legacy and should remain masked/inactive.
- Do not treat this project as the live relay runtime going forward.
