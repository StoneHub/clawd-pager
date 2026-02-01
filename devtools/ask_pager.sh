#!/bin/bash
# Simple wrapper to ask questions via pager
# Usage: ./ask_pager.sh "Your question here?" [timeout]

QUESTION="$1"
TIMEOUT="${2:-60}"

python3 /home/monroe/clawd/work/clawd-pager/devtools/claude_hook.py ask "$QUESTION" --timeout "$TIMEOUT"
