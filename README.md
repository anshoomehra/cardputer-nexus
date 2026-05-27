# Claude Nexus

**A pocket companion for Claude Code** — two-way communication between your AI coding assistant and an M5Stack Cardputer you can carry in your pocket.

```
┌─────────────────────────────────────────────────────────────────┐
│                         ARCHITECTURE                            │
│                                                                 │
│  ┌──────────────┐         BLE          ┌──────────────────┐    │
│  │  Cardputer   │◄────────────────────►│   Host Proxy     │    │
│  │              │    Nordic UART       │   (debug_demo)   │    │
│  │  Claude      │      Service         │                  │    │
│  │  Nexus App   │                      │  HTTP :8765      │    │
│  │              │                      │    ▲             │    │
│  │  - 4 Pets    │                      │    │             │    │
│  │  - Sounds    │                      │    ▼             │    │
│  │  - Keyboard  │                      │  File Watcher    │    │
│  └──────────────┘                      └────────┬─────────┘    │
│        ▲                                        │              │
│        │ Notifications                          │ Commands     │
│        │ Token Stats                            │              │
│        │ Waiting Alerts                         ▼              │
│        │                               ┌──────────────────┐    │
│        └───────────────────────────────│   Claude Code    │    │
│                                        │                  │    │
│                                        │  Your AI Coding  │    │
│                                        │  Assistant       │    │
│                                        └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## What It Does

| Direction | Feature | How |
|-----------|---------|-----|
| **Claude Code → Device** | Notifications | `curl localhost:8765/notify` |
| **Claude Code → Device** | Token usage stats | `curl localhost:8765/stats` |
| **Claude Code → Device** | "Waiting for input" alerts | `curl localhost:8765/waiting` |
| **Device → Claude Code** | Text commands | Press T, type, press Enter |

## Features

### Pet Companions
Four ASCII pets with emotions — press **P** to cycle:
- **Cat** — Classic companion
- **Dog** — Tail wags while waiting!
- **Blob** — Friendly amorphous friend
- **Bunny** — Cute and alert

Each pet has moods: idle, happy, alert, sleep

### Sound Alerts
Different tones for different urgencies:
- **Info** — Single chirp
- **Warning** — Two ascending tones
- **Critical** — Three rapid alternating tones

### Token Usage Display
See your session's token consumption in the top bar (updates live)

### Idle Alerts
After 5 minutes of no activity, your pet falls asleep and you get a gentle reminder beep

---

## Quick Start

### Prerequisites
- M5Stack Cardputer ADV (with speaker)
- Python 3.10+
- Claude Code
- macOS (tested), Linux (should work)

### 1. Clone & Setup

```bash
git clone https://github.com/anshoomehra/cardputer-nexus.git
cd cardputer-nexus

# Install host dependencies
cd host
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install aiohttp  # For HTTP API
```

### 2. Flash Device

Connect Cardputer via USB-C:

```bash
# Install mpremote if needed
pip install mpremote

# Copy the app to device
python -m mpremote connect /dev/tty.usbmodem101 cp buddy/device/apps/claude_nexus.py :/flash/apps/claude_nexus.py
```

### 3. Configure (Optional - For Voice Features)

```bash
cd host
cp config.example.py config.py
```

Edit `config.py`:
```python
# Option A: Use your own Anthropic API key
CLAUDE_API_KEY = "sk-ant-..."
CLAUDE_ENDPOINT = "https://api.anthropic.com"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Option B: Use a local/enterprise endpoint (no API key needed)
CLAUDE_ENDPOINT = "http://localhost:9999"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_API_KEY = ""  # Leave empty for local endpoints
```

### 4. Run

**Terminal 1 — Host Proxy:**
```bash
cd host
source .venv/bin/activate
python debug_demo.py
```

**Terminal 2 — Device:**
1. Reset Cardputer
2. Select **Claude Nexus** from app menu
3. Wait for "LINKED" status

### 5. Test It!

```bash
# Send a notification
curl -X POST http://localhost:8765/notify \
  -H "Content-Type: application/json" \
  -d '{"title":"Hello!","body":"From Claude Code","urgency":"info"}'

# Send token stats
curl -X POST http://localhost:8765/stats \
  -H "Content-Type: application/json" \
  -d '{"tokens":50000}'

# Alert that Claude is waiting
curl -X POST http://localhost:8765/waiting \
  -H "Content-Type: application/json" \
  -d '{"body":"What should I do next?"}'
```

---

## Device Controls

| Key | Action |
|-----|--------|
| **T** or **Space** | Open text input |
| **P** | Cycle pet (Cat → Dog → Blob → Bunny) |
| **Q** | Quit app |
| **Enter** | Send message (in text mode) |
| **Esc** | Cancel text input |
| **Space** | Dismiss notification |

---

## HTTP API Reference

### POST /notify
Send a notification to the device.

```json
{
  "title": "Build Complete",
  "body": "All tests passed",
  "urgency": "info"  // "info" | "warn" | "crit"
}
```

### POST /stats
Update token usage display.

```json
{
  "tokens": 125000
}
```

### POST /waiting
Alert that Claude Code is waiting for input.

```json
{
  "body": "Waiting for your instructions..."
}
```

---

## MCP Server (Alternative)

Instead of the HTTP proxy, you can use the MCP server for direct Claude Code integration.

### Setup

```bash
cd mcp
pip install -r requirements.txt

# Register with Claude Code
claude mcp add cardputer -- python "$(pwd)/server.py"
```

### Available Tools

Once registered, Claude Code can call these tools directly:

| Tool | Description |
|------|-------------|
| `notify(title, body, urgency)` | Send notification to device |
| `ask(question, choices)` | Ask user to choose from options |
| `confirm(title)` | Request confirmation (hold Y for 2s) |

### Example Usage in Claude Code

```
"Send a notification to my Cardputer saying the build is complete"
→ Claude calls: notify(title="Build", body="Complete!", urgency="info")

"Ask me on my Cardputer which env to deploy to"  
→ Claude calls: ask(question="Deploy to?", choices=["dev","staging","prod"])
```

**Note:** MCP and HTTP proxy both need BLE connection - only run one at a time.


---

## Project Structure

```
cardputer-nexus/
├── buddy/device/apps/
│   └── claude_nexus.py      # Main device app (MicroPython)
├── host/
│   ├── debug_demo.py        # BLE proxy with HTTP API
│   ├── config.example.py    # Configuration template
│   └── requirements.txt
├── mcp/
│   └── server.py            # MCP server (alternative to proxy)
└── README.md
```

---

## Troubleshooting

### Device not connecting
- Make sure USB is disconnected (BLE only allows one connection)
- Restart the proxy
- Reset the device and relaunch the app

### No sound
- Original Cardputer has no speaker — you need **Cardputer ADV**
- Sound plays but is quiet? We set volume to max (255)

### Keyboard not responding
- There's an 800ms delay after M5.begin() before keyboard works
- This is handled automatically in the app

---

## Integration with Claude Code

To receive commands from your Cardputer in Claude Code, set up a file watcher:

```bash
# The proxy writes commands to this file
cat ~/.cardputer_voice_cmd

# Watch for changes (in your Claude Code session)
# Claude Code can monitor this file and respond to commands
```

---

## Credits

- **Pet system inspired by**: [y88huang/claude-desktop-buddy-cardputer](https://github.com/y88huang/claude-desktop-buddy-cardputer)
- **Original voice AI**: [dakshaymehta/cardputer-claude-os](https://github.com/dakshaymehta/cardputer-claude-os)
- **m5-onboard skill**: [moremas/build-with-claude](https://github.com/moremas/build-with-claude)

---

## Important Notes

- **This works with Claude Code (CLI)**, not Claude Desktop
- Voice features require the Cardputer ADV variant (with mic/speaker)
- Text input mode works on all Cardputer variants

---

## License

Apache 2.0 — See [LICENSE](LICENSE)

---

<p align="center">
  <strong>Your pocket AI companion</strong>
</p>

---

## Receiving Commands in Claude Code

When you send a command from the Cardputer (press T, type, Enter), the proxy writes it to `~/.cardputer_voice_cmd`. 

### Option 1: Ask Claude Code to Watch

Simply tell Claude Code:
> "Watch ~/.cardputer_voice_cmd for commands from my Cardputer and execute them"

Claude Code will set up a file monitor and respond to your commands.

### Option 2: Manual File Watch

```bash
# In a terminal, watch for new commands:
last=""; while true; do 
  current=$(cat ~/.cardputer_voice_cmd 2>/dev/null)
  if [ -n "$current" ] && [ "$current" != "$last" ]; then 
    echo "Command: $current"
    last="$current"
  fi
  sleep 1
done
```

### How It Works

```
┌─────────────┐      BLE       ┌─────────────┐     File      ┌─────────────┐
│  Cardputer  │ ────────────►  │   Proxy     │ ───────────►  │ Claude Code │
│  (T + type) │                │             │               │             │
│             │  ◄──────────── │  HTTP API   │  ◄─────────── │  (responds) │
│  (display)  │   Notification │  :8765      │   curl/notify │             │
└─────────────┘                └─────────────┘               └─────────────┘
```

The proxy bridges both directions:
- **Device → Claude Code**: Writes to `~/.cardputer_voice_cmd`
- **Claude Code → Device**: HTTP POST to `localhost:8765/notify`
