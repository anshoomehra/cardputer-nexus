<p align="center">
  <img src="docs/assets/nexus-banner.png" alt="Cardputer Nexus" width="600">
</p>

<h1 align="center">Cardputer Nexus</h1>

<p align="center">
  <strong>The nexus between human intent and AI action</strong>
</p>

<p align="center">
  Voice control, hardware confirmations, and MCP tools for Claude on M5Stack Cardputer
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#local-voice-setup">Local Voice</a> •
  <a href="#mcp-tools">MCP Tools</a> •
  <a href="#enterprise">Enterprise</a> •
  <a href="#credits">Credits</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-M5Stack%20Cardputer-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/claude-Opus%204.6-blueviolet?style=flat-square" alt="Claude">
  <img src="https://img.shields.io/badge/protocol-MCP-green?style=flat-square" alt="MCP">
  <img src="https://img.shields.io/badge/license-Apache%202.0-orange?style=flat-square" alt="License">
</p>

---

## Why Nexus?

> **"A prompt injection cannot press your buttons."**

Cardputer Nexus transforms your M5Stack Cardputer into the **physical control layer** for Claude AI agents. When AI can execute code, deploy to production, or delete data—you need more than a software "Allow" button.

| Attack Vector | Software Dialog | Nexus Hardware |
|---------------|-----------------|----------------|
| Prompt injection tricks approval | ❌ Vulnerable | ✅ Cannot press physical button |
| UI spoofing | ❌ Vulnerable | ✅ Separate device |
| Fatigue clicking | ❌ Common | ✅ Requires sustained 2s press |
| Audit trail | ❌ Modifiable | ✅ Device-attested |

---

## Features

### 🎤 Push to Claude (Voice AI)

Hold SPACE to talk, release to send. Supports **two modes**:

**Cloud Mode (Original):** Cardputer → Cloudflare Worker → Whisper → Claude Haiku 4.5

**Local Mode (New):** Cardputer → Your Mac → Local Whisper → **Your Enterprise Claude (localhost:9999)**

```
┌─────────────────┐     BLE      ┌──────────────────────┐
│   Cardputer     │ ──────────►  │  Your MacBook        │
│   [SPACE held]  │              │  - Local Whisper     │
│   "Deploy to    │  ◄────────── │  - Enterprise Claude │
│    staging"     │   Response   │  - Opus 4.6          │
└─────────────────┘              └──────────────────────┘
```

### 🔐 Hardware MCP Server

Your Cardputer becomes an MCP server that Claude Code, Claude Desktop, Cursor, or any MCP-speaking agent can call:

| Tool | Function | Security Level |
|------|----------|----------------|
| `notify(title, body, urgency)` | Flash banner + sound | Informational |
| `ask(question, choices, timeout)` | Multiple choice via keys 1-4 | Decision |
| `confirm(title, timeout)` | **Sustained 2s keypress required** | ⚠️ Critical |

**The `confirm()` Security Model:**

```
┌────────────────────────────┐
│  ⚠️  DANGER  ⚠️             │
│                            │
│  DROP TABLE users?         │
│                            │
│  ████████░░ HOLD [Y] 2s    │
│  or press [N] to cancel    │
└────────────────────────────┘
```

A prompt injection **cannot physically hold down a key** for 2 seconds. Only you can.

### 📟 Claude Pager (Managed Agents)

Monitor your Managed Agents sessions from your pocket:

| Screen | Function |
|--------|----------|
| **Compose** | Fire off tasks as Managed Agent sessions |
| **Inbox** | Live status: `bash: pytest…`, `wrote auth_test.py` |
| **Detail** | Reply, interrupt, or approve pending tool calls |

### 🐾 Pet Companions (Coming Soon)

Tamagotchi-style creatures that react to your Claude usage — 20 species, 7 moods. *Inspired by [y88huang/claude-desktop-buddy-cardputer](https://github.com/y88huang/claude-desktop-buddy-cardputer).*

---

## Quick Start

### Prerequisites

- M5Stack Cardputer ADV (with mic/speaker for voice)
- Python 3.10+
- Claude Code

### Flash the Device

```bash
# Clone this repo
git clone https://github.com/anshoomehra/cardputer-nexus.git
cd cardputer-nexus

# Plug in Cardputer via USB-C
# Open Claude Code, point to this folder
# Type:
m5-onboard go
```

**When prompted for download mode:**
1. Hold **G0** button (on back)
2. While holding, press **Reset**
3. Release Reset first, then G0
4. Screen goes dark = ready

### Connect to Claude Desktop

1. On Cardputer: Select **Claude Buddy** from menu
2. In Claude Desktop: **Help → Troubleshooting → Enable Developer Mode**
3. **Developer → Hardware Buddy → Connect**
4. Select your device

### Set Up MCP Server

```bash
# On Cardputer: Select cardputer_mcp from menu

# On Mac:
cd mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Register with Claude Code
claude mcp add cardputer "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

Now Claude can call `notify()`, `ask()`, and `confirm()`!

---

## Local Voice Setup (No Cloud)

Replace Cloudflare Worker with **local processing** using your enterprise Claude:

### 1. Install Dependencies

```bash
cd host
pip install -r requirements.txt

# Install Whisper locally
pip install openai-whisper
```

### 2. Configure

```bash
cp config.example.py config.py
```

Edit `config.py`:
```python
# Your enterprise Claude endpoint
CLAUDE_ENDPOINT = "http://localhost:9999"
CLAUDE_MODEL = "claude-opus-4-6"

# Local Whisper
STT_BACKEND = "whisper_local"
WHISPER_MODEL = "base"  # tiny|base|small|medium|large
```

### 3. Run

```bash
python local_proxy.py
```

Voice now flows: **Cardputer → BLE → Mac (Whisper) → localhost:9999 (Opus 4.6) → Cardputer**

✅ No Cloudflare  
✅ No API costs (using your enterprise Claude)  
✅ All data stays local  

---

## MCP Tools Reference

### `notify`

```json
{
  "tool": "cardputer.notify",
  "input": {
    "title": "Build Complete",
    "body": "47 tests passed",
    "urgency": "low"
  }
}
```

| Urgency | Color | Sound |
|---------|-------|-------|
| `low` | Green | Single chirp |
| `medium` | Yellow | Double beep |
| `high` | Red | Triple alarm |

### `ask`

```json
{
  "tool": "cardputer.ask",
  "input": {
    "question": "Which environment?",
    "choices": ["dev", "staging", "prod"],
    "timeout_s": 30
  }
}
```

Returns: `{"choice": "staging", "index": 1}`

### `confirm`

```json
{
  "tool": "cardputer.confirm",
  "input": {
    "title": "DELETE production database?",
    "timeout_s": 60
  }
}
```

Requires **holding Y key for 2 seconds**. Returns: `{"confirmed": true|false}`

---

## Enterprise

See [docs/enterprise.md](docs/enterprise.md) for:

- Fleet deployment (batch flashing hundreds of devices)
- Central configuration management
- Audit logging and compliance
- SOC 2 / HIPAA / PCI considerations

### Why Nexus for Enterprise?

| Challenge | Solution |
|-----------|----------|
| Prompt injection | `confirm()` requires physical gesture |
| Audit trail | Device-attested approval logs |
| Data sovereignty | Local Whisper + your Claude endpoint |
| Fleet scale | Same firmware, central config, OTA updates |
| Cost control | Built-in daily spawn caps |

---

## Project Structure

```
cardputer-nexus/
├── buddy/                    # Device firmware (MicroPython)
│   ├── device/apps/          # Apps: claude_buddy, push_to_claude, pager, mcp
│   └── scripts/              # Install scripts
├── host/                     # NEW: Local proxy (no Cloudflare)
│   ├── config.example.py     # Configuration template
│   ├── local_proxy.py        # Whisper + Claude bridge
│   └── requirements.txt
├── mcp/                      # MCP server (BLE bridge)
│   └── server.py
├── worker/                   # Cloudflare Worker (optional)
├── mac/                      # macOS artifact sync
├── .claude/skills/           # Claude Code skills
└── docs/
    └── enterprise.md         # Enterprise deployment guide
```

---

## Credits & Attribution

### Forked From

**[dakshaymehta/cardputer-claude-os](https://github.com/dakshaymehta/cardputer-claude-os)**

This project is a fork of the excellent `cardputer-claude-os` by [@dakshaymehta](https://github.com/dakshaymehta). The core voice AI, Claude Pager, and MCP server functionality originates from this project. We are deeply grateful for this foundational work.

### Upstream Origin

**[moremas/build-with-claude](https://github.com/moremas/build-with-claude)**

The original `m5-onboard` skill and device launcher come from this project.

### Pet System (Planned Integration)

**[y88huang/claude-desktop-buddy-cardputer](https://github.com/y88huang/claude-desktop-buddy-cardputer)**

The planned Tamagotchi-style pet companion system will be adapted from [@y88huang](https://github.com/y88huang)'s fantastic Cardputer port. The 20 ASCII species, 7 mood states, and emotional engagement mechanics originate from this project.

### Protocol Reference

**[anthropics/claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy)**

The BLE protocol and Hardware Buddy integration is based on the official Anthropic reference implementation.

---

## What's New in This Fork

| Addition | Description |
|----------|-------------|
| **Local Voice Proxy** | Whisper + enterprise Claude on localhost (no Cloudflare needed) |
| **Enterprise Docs** | Fleet deployment, compliance, audit logging |
| **Nexus Branding** | New README, tagline, security messaging |
| **Pet Integration Plan** | Framework for y88huang's companion system |

---

## License

Apache 2.0 — See [LICENSE](LICENSE)

---

<p align="center">
  <strong>Your buttons. Your rules.</strong>
</p>

<p align="center">
  <sub>Made with ❤️ for the Claude community</sub>
</p>
