# Changelog

All notable changes to Cardputer Nexus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Local Voice Proxy** (`host/local_proxy.py`)
  - Local Whisper STT support (no Cloudflare needed)
  - Enterprise Claude endpoint configuration (localhost:9999)
  - macOS native dictation placeholder
- **Enterprise Documentation** (`docs/enterprise.md`)
  - Fleet deployment guide
  - Compliance considerations (SOC 2, HIPAA, PCI)
  - Audit logging setup
- **Nexus Branding**
  - New README with security-focused messaging
  - Updated NOTICE with full attribution
- **Pet Integration Plan**
  - Framework for y88huang's companion system (coming soon)

### Changed
- Restructured README for Nexus identity
- Added proper credits to all upstream projects

### Inherited from cardputer-claude-os
- Claude Buddy BLE connection
- Push to Claude (Voice + Chat via Cloudflare)
- Claude Pager (Managed Agents)
- Cardputer MCP server
- Auto-discovery app launcher
- Central Console browser UI
- Mac artifact sync

---

## Attribution

This project stands on the shoulders of giants:

- **dakshaymehta/cardputer-claude-os** — Core voice AI, pager, and MCP functionality
- **moremas/build-with-claude** — m5-onboard Claude Code skill
- **y88huang/claude-desktop-buddy-cardputer** — Pet companion system (planned)
- **anthropics/claude-desktop-buddy** — BLE protocol reference
