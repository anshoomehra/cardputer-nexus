#!/bin/bash
# Claude Nexus — Auto-configure Claude Code hooks
# Run: bash setup_hooks.sh

set -e

SETTINGS_FILE="$HOME/.claude/settings.json"
HOOK_COMMAND='LOCK=/tmp/.cardputer_waiting_lock; if [ -f \"$LOCK\" ] && [ $(($(date +%s) - $(cat \"$LOCK\"))) -lt 120 ]; then exit 0; fi; date +%s > \"$LOCK\"; curl -s -X POST http://localhost:8765/waiting -H '"'"'Content-Type: application/json'"'"' -d '"'"'{"body":"Claude Code is waiting for input"}'"'"' > /dev/null 2>&1 || true'

echo "╔══════════════════════════════════════════╗"
echo "║   Claude Nexus — Hook Setup              ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if settings.json exists
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "Creating $SETTINGS_FILE..."
    mkdir -p "$HOME/.claude"
    echo '{}' > "$SETTINGS_FILE"
fi

# Check if hooks already configured
if grep -q "cardputer_waiting_lock" "$SETTINGS_FILE" 2>/dev/null; then
    echo "✓ Hooks already configured in $SETTINGS_FILE"
    echo "  Nothing to do!"
    exit 0
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "⚠ jq not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install jq
    else
        echo "✗ Please install jq: brew install jq (or apt-get install jq)"
        exit 1
    fi
fi

# Add hooks to settings.json
echo "Adding Stop hook to $SETTINGS_FILE..."
TMP=$(mktemp)
jq '.hooks.Stop = [{"hooks": [{"type": "command", "command": "LOCK=/tmp/.cardputer_waiting_lock; if [ -f \"$LOCK\" ] && [ $(($(date +%s) - $(cat \"$LOCK\"))) -lt 120 ]; then exit 0; fi; date +%s > \"$LOCK\"; curl -s -X POST http://localhost:8765/waiting -H '\''Content-Type: application/json'\'' -d '\''{ \"body\": \"Claude Code is waiting for input\" }'\'' > /dev/null 2>&1 || true"}]}]' "$SETTINGS_FILE" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"

echo ""
echo "✓ Hook installed!"
echo ""
echo "What it does:"
echo "  When Claude Code finishes and waits for your input,"
echo "  your Cardputer will beep and show a notification."
echo "  (Max once every 2 minutes to avoid spam)"
echo ""
echo "Prerequisites:"
echo "  1. Proxy running: cd host && python debug_demo.py"
echo "  2. Cardputer running Claude Nexus and showing LINKED"
echo ""
echo "To remove: edit $SETTINGS_FILE and delete the 'hooks' section"
