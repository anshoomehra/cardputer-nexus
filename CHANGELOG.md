# Changelog

All notable changes to Cardputer Nexus will be documented in this file.

## [0.3.0] - 2026-05-27

### Added
- **Voice Commands** — Press V to record from Mac mic, transcribed with Whisper
  - Host proxy records 5s audio via `sounddevice`
  - Local Whisper STT transcription
  - Result sent to Claude Code as command
  - Also available via `POST /voice` HTTP endpoint
- **Sleep/Wake Fix** — Pressing T/V while sleeping just wakes up without triggering text/voice mode

### Known Issues
- **On-device mic not working** — The Cardputer ADV routes its microphone through an ES8311 audio codec (I2C address 0x18). The UIFlow 2.0 MicroPython firmware does not properly initialize the ES8311's ADC recording path, causing all mic captures to return silence. This is a firmware limitation (not a hardware defect) and affects all Cardputer ADV units running UIFlow 2.0. Voice commands work via Mac mic as a workaround.

## [0.2.0] - 2026-05-26

### Added
- **Claude Nexus App** - Unified companion with two-way Claude Code communication
  - 4 ASCII pets (Cat, Dog with tail wag, Blob, Bunny)
  - Sound alerts with urgency levels (info/warn/crit)
  - Token usage display in top bar
  - Idle detection with sleeping pet animation
  - Text input mode for sending commands to Claude Code
- **Host Proxy** (`host/debug_demo.py`)
  - BLE proxy bridging device to Claude Code
  - HTTP API endpoints: /notify, /stats, /waiting
  - Writes device commands to ~/.cardputer_voice_cmd
- **API Key Support**
  - Direct Anthropic API usage (config.example.py)
  - Also supports local endpoints

### Changed
- Updated MCP server to use Nordic UART Service UUIDs
- Simplified README with architecture diagram
- Clarified this works with Claude Code CLI, not Desktop

### Removed
- Redundant apps (keep nexus, pager, snake)

## [0.1.0] - Initial Fork

### Inherited from upstream
- Claude Buddy BLE connection
- Push to Claude (Voice + Chat)
- Claude Pager (Managed Agents)
- Cardputer MCP server
- Auto-discovery app launcher

---

## Attribution

This project stands on the shoulders of giants:

- **dakshaymehta/cardputer-claude-os** — Core voice AI, pager, and MCP functionality
- **moremas/build-with-claude** — m5-onboard Claude Code skill
- **y88huang/claude-desktop-buddy-cardputer** — Pet companion system inspiration
- **anthropics/claude-desktop-buddy** — BLE protocol reference
