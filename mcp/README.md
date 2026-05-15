# cardputer-mcp

A Model Context Protocol server that gives any Claude (Code, Desktop,
Managed Agents — anything that speaks MCP) a physical channel to the
user via their Cardputer.

The Cardputer becomes the agent's pocket pager: it can buzz the user,
ask a multiple-choice question, demand physical confirmation for
destructive operations, dictate via the mic, and display ambient
status — all without the user needing to refocus to their laptop.

## Status — iteration 2 (real BLE; notify + ask end-to-end)

The host-side bridge speaks Bluetooth Low Energy via `bleak` to the
`cardputer_mcp.py` device app. Two tools work end-to-end:

| Tool                                | iter 2                           | iter 3                     | iter 4                      |
| ----------------------------------- | -------------------------------- | -------------------------- | --------------------------- |
| `notify(title, body, urgency)`      | ✅ visual banner + speaker chirp | rate-limit, per-agent tags | —                           |
| `ask(question, choices, timeout_s)` | ✅ blocks on QWERTY input        | DND awareness              | —                           |
| `confirm(title, danger)`            | —                                | hold-Y-3s physical gesture | —                           |
| `show(text, channel)`               | —                                | —                          | ambient line on LCD         |
| `dictate(prompt, max_seconds)`      | —                                | —                          | mic → Worker/Whisper → text |

## Architecture

```
┌─────────────────────────┐  stdio  ┌─────────────────────┐
│ Claude Code / Desktop / │◄───────►│  cardputer-mcp      │
│ Cursor / any MCP client │         │  (this directory,   │
│                         │         │   bleak transport)  │
└─────────────────────────┘         └──────────┬──────────┘
                                               │ BLE GATT
                                               │ Service: a5cd0001-…
                                               │ RX: a5cd0002-… (host → device)
                                               │ TX: a5cd0003-… (device → host)
                                               ▼
                                    ┌─────────────────────┐
                                    │   Cardputer         │
                                    │   buddy/device/apps │
                                    │   /cardputer_mcp.py │
                                    └─────────────────────┘
```

The BLE service uses a UUID block (`a5cd0001-…`) distinct from the
Nordic UART Service that Buddy uses (`6e400001-…`). The two apps
can't run on the device at the same time (you pick one from the
launcher, and exiting an app `machine.reset()`s the whole stack
anyway), but the separation lets the wire formats evolve
independently and means a future build could host both peripherals
side-by-side without contention.

Wire format is documented in
[`buddy/references/mcp_protocol.md`](../buddy/references/mcp_protocol.md).

## Why local stdio first (not the Cloudflare Worker)

Two reasons:

1. **Latency.** BLE is ~50–100 ms round-trip; a Worker hop adds
   internet RTT for no benefit when the user's laptop and pocket
   are in the same room. The whole point of the device is that
   the interaction feels instant.
2. **No new secrets.** Stdio runs as the user. The MCP client (Claude
   Code) talks to the device via BLE locally; nothing transits the
   public internet. The Worker-bridged HTTPS transport will land
   later for cloud agents that can't reach BLE (Managed Agents
   sessions, claude.ai with the MCP connector).

## Install + first run

```bash
cd mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Point Claude Code at the server. The full python path is required
# because Claude Code's MCP runner doesn't know about your venv.
claude mcp add cardputer "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

Push the device app, boot it, then in a fresh Claude Code session:

```bash
# Push apps to the device (no firmware re-flash needed).
python3 .claude/skills/m5-onboard/scripts/install_apps.py --port <PORT> --src buddy
```

Reboot the device, pick **cardputer_mcp** from the launcher menu.
The screen will read `waiting for bridge` until the first tool call
triggers the host to scan and connect. Once connected the screen
flips to a green `READY`.

Then in Claude Code, try:

> Use the cardputer notify tool to tell me 'tests passing'.

The Cardputer's screen flips to a notification banner, plays a soft
chirp, and auto-clears after 5 s. The tool returns `"shown"` to
Claude.

For `ask`:

> Use cardputer.ask to ask "deploy now?" with choices ["yes", "no"]
> and a 30 second timeout.

The device shows the question with numbered choices. Press `1` or
`2` on the Cardputer's QWERTY; Claude gets back the choice string.
Press `ESC` on the device to cancel — Claude gets `"cancelled"`.

### macOS Bluetooth permission

On macOS the first scan triggers a permission prompt. Approve it
once; bleak caches the grant for future sessions. If Claude Code
runs in a sandboxed context (some terminal multiplexers) you may
need to explicitly grant Bluetooth to the terminal app itself
under System Settings → Privacy & Security → Bluetooth.

### Connection caching

After the first successful connect, the device's BLE address is
saved to `~/.cardputer-mcp/paired.json`. Subsequent calls skip the
scan (faster startup). If the cached address fails (different
device, address changed), we fall back to a fresh scan and update
the cache.

### Backoff when device is off

If a scan finds no Cardputer, the bridge stops trying for 30 s. This
prevents every tool call from eating a 5 s scan timeout while the
device is simply not powered on — Claude gets a fast
`"unavailable: …"` instead.

## Tool descriptions matter

The single biggest lever for "does Claude actually call this tool
when it should?" is the tool description. The descriptions in
`server.py` are tuned for Claude — they include:

- a one-sentence summary of what the tool does
- a "use when…" line that names a specific scenario
- size constraints (240×135 is tiny — agents need to be told)
- the exact return-value contract

When iterating on these, validate by giving Claude a prompt like
"the user is away from their laptop, ask if they want to deploy"
and seeing whether it reaches for `cardputer.ask` unprompted. If
not, the description is too generic — make it more specific to the
scenario.

## Wire-protocol notes carried over from Buddy

The device-side code in `cardputer_mcp.py` mirrors `buddy_ble.py`'s
patterns in detail because the same hard-won lessons apply:

- **Init order is load-bearing.** `BLE()` → sleep → `active(True)` →
  settle → `config(gap_name)` → `gatts_register_services` → first
  `gap_advertise` → THEN `gatts_set_buffer`. Reordering produces
  silent failures (controller wedges, dropped bytes, payloads that
  refuse to advertise).
- **IRQ handlers buffer-and-dispatch.** RX bytes accumulate in a
  bytearray; complete lines are split on `\n` and handed up.
- **Re-advertise is scheduler-deferred.** Inline `gap_advertise`
  the instant a disconnect IRQ fires returns OSError(-30) on this
  build; we use `micropython.schedule` and a 150/300/450/600/750 ms
  staircase of retries.
- **Cascade advertising fallback.** Five payload shapes, from rich
  (UUID + name) to empty, so the device shows up SOMETHING even
  when NimBLE is wedged.
- **20-byte MTU chunking.** Default ATT MTU on ESP32 is 23 → 20
  bytes of payload. Both sides chunk every write; the receiver
  reassembles on `\n`.

See `buddy/references/ble_on_micropython.md` for the full list of
MicroPython BLE gotchas these patterns paper over.

## Roadmap

- [x] iter 1: scaffold with stubbed transport
- [x] iter 2: real BLE transport; `notify` and `ask` end-to-end
- [ ] iter 3: `confirm` (hold-Y-3s); per-agent tags + rate limit;
      DND switch
- [ ] iter 4: `show` (ambient line on LCD); `dictate` (mic →
      Worker/Whisper → text)
- [ ] iter 5: Worker-bridged HTTPS MCP for cloud agents
- [ ] iter 6: inverse direction — programmable launcher buttons
      that fire Managed Agents tasks

## License

Same as the parent project (Apache 2.0).
