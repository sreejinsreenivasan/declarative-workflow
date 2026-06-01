#!/usr/bin/env bash
# Runs before every Bash tool call.
# Blocks destructive operations and enforces quality checks on Python edits.

COMMAND="$1"

# Block destructive git operations
if echo "$COMMAND" | grep -qE "git (push --force|reset --hard|clean -f|branch -D)"; then
  echo "BLOCKED: Destructive git operation requires explicit user approval."
  exit 1
fi

# Block force push to main/master
if echo "$COMMAND" | grep -qE "git push.*(main|master).*--force"; then
  echo "BLOCKED: Force push to main/master is not allowed."
  exit 1
fi

# Warn on rm -rf
if echo "$COMMAND" | grep -qE "rm -rf"; then
  echo "WARNING: rm -rf detected. Confirm this is intentional."
fi

exit 0
