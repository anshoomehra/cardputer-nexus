# Enterprise Deployment Guide

This guide covers deploying Cardputer Nexus at scale across an organization.

## Table of Contents

1. [Why Nexus for Enterprise](#why-nexus-for-enterprise)
2. [Security Model](#security-model)
3. [Fleet Deployment](#fleet-deployment)
4. [Configuration Management](#configuration-management)
5. [Monitoring & Auditing](#monitoring--auditing)
6. [Compliance](#compliance)

---

## Why Nexus for Enterprise

### The Problem

AI agents like Claude Code can execute arbitrary code, access filesystems, and deploy to production. Traditional software dialogs are vulnerable to:

1. **Prompt injection** - Malicious prompts trick the AI into clicking "Allow"
2. **UI spoofing** - Fake dialogs that look legitimate
3. **Fatigue clicking** - Users habitually clicking "Allow"
4. **Audit gaps** - No hardware-verified approval records

### The Nexus Solution

Physical hardware confirmations that **cannot be bypassed by software**:

| Attack Vector | Software Dialog | Nexus Hardware |
|---------------|-----------------|----------------|
| Prompt injection | ❌ Vulnerable | ✅ Cannot press physical button |
| UI spoofing | ❌ Vulnerable | ✅ Separate device |
| Fatigue clicking | ❌ Common | ✅ Requires sustained 2s press |
| Audit trail | ❌ Modifiable | ✅ Device-attested |

---

## Security Model

### The `confirm()` Tool

The core security feature requires **physical gesture**:

```python
await mcp.call("cardputer.confirm", {
    "title": "DELETE production database?",
    "timeout_s": 60
})
```

**Security properties:**

1. **Physical gesture required** - Hold `Y` key for 2+ seconds
2. **Visual confirmation** - Red danger banner on separate device
3. **Timeout** - Auto-denies if no response
4. **No remote trigger** - BLE only (~10m range)
5. **Device attestation** - Response signed with device key

### What Nexus Does NOT Protect Against

- Physical access by attacker
- User intentionally approving malicious actions
- Attacks that don't require `confirm()`

---

## Fleet Deployment

### Hardware

**Recommended:** M5Stack Cardputer ADV

- Bulk orders: [shop.m5stack.com](https://shop.m5stack.com)
- ~$50/device

### Batch Flashing

```bash
# Flash multiple devices via USB hub
for port in /dev/tty.usbmodem*; do
    echo "Flashing $port..."
    esptool --chip esp32s3 --port $port \
        write_flash 0x0 releases/nexus-enterprise.bin
done
```

### Device Registration

```csv
device_id,mac_address,assigned_to,registered_at
NXS-001,AA:BB:CC:DD:EE:01,alice@company.com,2026-05-26
NXS-002,AA:BB:CC:DD:EE:02,bob@company.com,2026-05-26
```

---

## Configuration Management

### Central Config

```yaml
# nexus-fleet-config.yaml
version: 1
org_id: "acme-corp"

defaults:
  claude_endpoint: "https://claude.internal.com"
  claude_model: "claude-opus-4-6"
  
  mcp:
    confirm_hold_duration_ms: 2000
  
  audit:
    log_to_sd: true
    webhook_url: "https://audit.acme.com/nexus"

overrides:
  # Finance team: stricter
  - match: { department: "finance" }
    config:
      confirm_hold_duration_ms: 3000
```

### OTA Updates

```bash
python scripts/fleet_update.py \
    --firmware releases/nexus-v1.1.0.bin \
    --rollout-percent 10
```

---

## Monitoring & Auditing

### Audit Log Format

```json
{
  "timestamp": "2026-05-26T14:30:00Z",
  "device_id": "NXS-001",
  "event_type": "confirm_response",
  "details": {
    "title": "DELETE TABLE users",
    "response": "approved",
    "hold_duration_ms": 2340,
    "user_email": "alice@company.com"
  }
}
```

### Metrics

- Approval rate
- Response time
- Timeout rate
- Device health

---

## Compliance

### SOC 2

- CC6.1 - Access controls ✅
- CC6.7 - Restricting access ✅
- CC7.2 - Monitoring ✅

### HIPAA

- Set `include_transcripts: false` to avoid logging PHI
- Store audit logs in compliant infrastructure

### Sample Policy

> **AI Agent Authorization Policy**
> 
> All AI agent actions that modify production systems must be authorized 
> via Cardputer Nexus hardware confirmation. Software-only authorization 
> is not permitted for these operations.

---

*Document version: 1.0 | Last updated: May 2026*
