#!/usr/bin/env python3
"""
Cardputer Debug & Demo Tool - All-in-one debugging for your demo

Shows:
1. BLE scan results
2. Device connection state
3. All incoming/outgoing messages
4. Audio file analysis
5. Whisper transcription details

Features:
- Auto-reconnect when device disconnects
- Full debug logging
"""

import asyncio
import json
import os
import sys
import tempfile
import wave
import struct
from pathlib import Path
import time
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

try:
    import config
except ImportError:
    class config:
        WHISPER_MODEL = "base"
        WHISPER_DEVICE = "cpu"
        CLAUDE_ENDPOINT = "http://localhost:9999"
        CLAUDE_MODEL = "claude-sonnet-4-20250514"
        CLAUDE_API_KEY = ""

import whisper
import httpx
from bleak import BleakClient, BleakScanner

UART_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
UART_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

# Device prefixes to scan for
DEVICE_PREFIXES = ["ClaudeNexus_", "AskClaude_", "CCVoice_", "Anshoo's Nexus", "CardputerMCP_"]

# Colors for terminal output
class C:
    H = '\033[95m'
    B = '\033[94m'
    C = '\033[96m'
    G = '\033[92m'
    Y = '\033[93m'
    R = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(msg, color=None):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    if color:
        print(f"{color}[{ts}] {msg}{C.END}", flush=True)
    else:
        print(f"[{ts}] {msg}", flush=True)

def analyze_wav(data: bytes) -> dict:
    """Analyze WAV file header and content"""
    info = {}
    if len(data) < 44:
        info['error'] = 'Too short for WAV header'
        return info
    
    if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        info['valid_wav'] = True
        info['file_size'] = struct.unpack('<I', data[4:8])[0]
        info['format'] = data[8:12].decode()
        
        idx = 12
        while idx < len(data) - 8:
            chunk_id = data[idx:idx+4]
            chunk_size = struct.unpack('<I', data[idx+4:idx+8])[0]
            
            if chunk_id == b'fmt ':
                fmt_data = data[idx+8:idx+8+chunk_size]
                if len(fmt_data) >= 16:
                    audio_fmt = struct.unpack('<H', fmt_data[0:2])[0]
                    channels = struct.unpack('<H', fmt_data[2:4])[0]
                    sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                    bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
                    
                    info['audio_format'] = 'PCM' if audio_fmt == 1 else f'Other({audio_fmt})'
                    info['channels'] = channels
                    info['sample_rate'] = sample_rate
                    info['bits_per_sample'] = bits_per_sample
            
            elif chunk_id == b'data':
                info['data_size'] = chunk_size
                audio_data = data[idx+8:idx+8+min(chunk_size, 10000)]
                if len(audio_data) > 0 and info.get('bits_per_sample') == 16:
                    samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data[:len(audio_data)//2*2])
                    avg_amp = sum(abs(s) for s in samples) / len(samples)
                    max_amp = max(abs(s) for s in samples)
                    info['avg_amplitude'] = int(avg_amp)
                    info['max_amplitude'] = max_amp
                    info['is_likely_silence'] = avg_amp < 100
                break
            
            idx += 8 + chunk_size
    else:
        info['valid_wav'] = False
        info['header_bytes'] = data[:20].hex()
    
    return info


class DebugProxy:
    def __init__(self):
        log("Loading Whisper model...", C.C)
        self.whisper = whisper.load_model(config.WHISPER_MODEL, device=config.WHISPER_DEVICE)
        log("✓ Whisper ready", C.G)
        
        self.client = None
        self.device = None
        self.audio_buffer = bytearray()
        self.receiving_audio = False
        self.current_mode = None
        self.conversation = []
        self.audio_count = 0
        self.running = True
    
    async def scan_for_device(self):
        """Scan and find a Cardputer device"""
        log("Scanning for Cardputer...", C.C)
        
        devices = await BleakScanner.discover(timeout=5)
        
        for d in devices:
            name = d.name or ""
            if any(name.startswith(prefix) for prefix in DEVICE_PREFIXES):
                log(f"✓ Found: {name} ({d.address})", C.G)
                return d
        
        return None
    
    async def scan_all(self):
        """Scan and show ALL BLE devices"""
        log("━" * 50, C.C)
        log("SCANNING FOR BLE DEVICES...", C.BOLD)
        log("━" * 50, C.C)
        
        devices = await BleakScanner.discover(timeout=5)
        
        cardputer = None
        
        log(f"Found {len(devices)} devices:", C.Y)
        for d in devices:
            name = d.name or "(unnamed)"
            rssi = d.rssi if hasattr(d, 'rssi') else '?'
            
            is_cardputer = any(name.startswith(prefix) for prefix in DEVICE_PREFIXES)
            
            if is_cardputer:
                log(f"  ✓ {C.G}{name}{C.END} [{d.address}] RSSI: {rssi} {C.BOLD}← CARDPUTER{C.END}", C.G)
                cardputer = d
            else:
                log(f"    {name} [{d.address}] RSSI: {rssi}")
        
        log("━" * 50, C.C)
        return cardputer
    
    def on_disconnect(self, client):
        """Called when device disconnects"""
        log("━" * 50, C.Y)
        log("DEVICE DISCONNECTED", C.Y)
        log("Will attempt to reconnect...", C.Y)
        log("━" * 50, C.Y)
    
    async def connect(self, device):
        """Connect to device with disconnect callback"""
        log(f"Connecting to {device.name}...", C.Y)
        self.device = device
        self.client = BleakClient(device.address, disconnected_callback=self.on_disconnect)
        await self.client.connect()
        log(f"✓ Connected to {device.name}", C.G)
        
        log("Device services:", C.C)
        for service in self.client.services:
            log(f"  Service: {service.uuid}")
            for char in service.characteristics:
                props = ','.join(char.properties)
                log(f"    └─ {char.uuid} [{props}]")
        
        await self.client.start_notify(UART_TX_UUID, self._on_data)
        log(f"✓ Subscribed to notifications", C.G)
    
    async def _on_data(self, sender, data: bytearray):
        if self.receiving_audio:
            if len(data) < 100 and data[0:1] == b'{':
                try:
                    msg = json.loads(data.decode('utf-8'))
                    if msg.get("type") == "audio_end":
                        self.receiving_audio = False
                        log(f"AUDIO COMPLETE: {len(self.audio_buffer)} bytes", C.G)
                        await self._process_audio()
                        return
                except:
                    pass
            
            self.audio_buffer.extend(data)
            if len(self.audio_buffer) % 5000 < 500:
                log(f"  ← audio chunk: +{len(data)} bytes (total: {len(self.audio_buffer)})", C.B)
            return
        
        try:
            msg = json.loads(data.decode('utf-8'))
            log(f"← RECV: {json.dumps(msg)}", C.C)
            await self._handle_message(msg)
        except (json.JSONDecodeError, UnicodeDecodeError):
            log(f"← RAW DATA: {len(data)} bytes - {data[:50].hex()}...", C.Y)
    
    async def _handle_message(self, msg):
        msg_type = msg.get("type")
        mode = msg.get("mode", "ask_claude")
        
        if msg_type == "audio_start":
            self.audio_buffer = bytearray()
            self.receiving_audio = True
            self.current_mode = mode
            self.audio_count += 1
            self.audio_fmt = msg.get("fmt", "wav")
            self.audio_rate = msg.get("rate", 16000)
            log("━" * 50, C.H)
            log(f"AUDIO RECORDING #{self.audio_count} STARTED", C.BOLD)
            log(f"  Mode: {mode}, Format: {self.audio_fmt}, Rate: {self.audio_rate}", C.H)
            log(f"  Expected size: {msg.get('size')} bytes", C.H)
            log("━" * 50, C.H)
        
        elif msg_type == "text":
            text = msg.get("content", "")
            self.current_mode = mode
            log(f"TEXT INPUT: '{text}'", C.G)
            await self._process_text(text)

        elif msg_type == "voice_request":
            self.current_mode = mode
            log("━" * 50, C.H)
            log("VOICE REQUEST - Recording from Mac mic...", C.BOLD)
            log("━" * 50, C.H)
            asyncio.create_task(self._handle_voice_request(mode))
    
    async def _process_audio(self):
        log("━" * 50, C.Y)
        log("ANALYZING AUDIO FILE", C.BOLD)
        log("━" * 50, C.Y)
        
        if len(self.audio_buffer) < 1000:
            log("✗ Audio too short!", C.R)
            await self._send({"type": "error", "error": "Audio too short"})
            return

        # If raw PCM from device mic, wrap in WAV header
        audio_data = bytes(self.audio_buffer)
        if getattr(self, 'audio_fmt', 'wav') == 'pcm16':
            rate = getattr(self, 'audio_rate', 8000)
            log(f"Wrapping raw PCM in WAV (rate={rate})", C.C)
            data_size = len(audio_data)
            hdr = struct.pack('<4sI4s4sIHHIIHH4sI',
                b'RIFF', 36 + data_size, b'WAVE',
                b'fmt ', 16, 1, 1, rate, rate * 2, 2, 16,
                b'data', data_size)
            audio_data = hdr + audio_data

        wav_info = analyze_wav(audio_data)
        
        log("WAV File Analysis:", C.C)
        for key, value in wav_info.items():
            color = C.R if key == 'is_likely_silence' and value else C.G
            log(f"  {key}: {value}", color)
        
        debug_path = f"/tmp/cardputer_audio_{self.audio_count:03d}_{datetime.now().strftime('%H%M%S')}.wav"
        with open(debug_path, "wb") as f:
            f.write(audio_data)
        log(f"✓ Saved: {debug_path}", C.G)

        log("Transcribing with Whisper...", C.Y)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.whisper.transcribe(temp_path, verbose=False)
            )
            
            text = result["text"].strip()
            language = result.get("language", "?")
            
            log("━" * 50, C.G if text else C.R)
            if text:
                log(f"TRANSCRIPTION: \"{text}\"", C.G)
            else:
                log("TRANSCRIPTION: (empty - no speech detected)", C.R)
            log(f"  Language: {language}", C.C)
            log("━" * 50, C.G if text else C.R)
            
            if text:
                await self._process_text(text)
            else:
                if wav_info.get('is_likely_silence'):
                    await self._send({"type": "error", "error": "Mic captured silence - speak louder or check mic"})
                else:
                    await self._send({"type": "error", "error": "Could not understand - try again?"})
        
        except Exception as e:
            log(f"✗ Transcription error: {e}", C.R)
            await self._send({"type": "error", "error": str(e)})
        finally:
            os.unlink(temp_path)
    
    async def _process_text(self, text: str):
        if self.current_mode == "claude_code":
            await self._send_to_claude_code(text)
        else:
            await self._send_to_claude_api(text)

    async def _handle_voice_request(self, mode: str):
        """Record from Mac mic, transcribe with Whisper, send result back."""
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            log("✗ sounddevice not installed: pip install sounddevice numpy", C.R)
            await self._send({"type": "voice_result", "text": ""})
            return

        try:
            # Notify device we're recording
            await self._send({"type": "voice_status", "status": "listening"})

            # Record from Mac mic
            duration = 5  # seconds
            sample_rate = 16000
            log(f"Recording {duration}s from Mac mic (16kHz)...", C.Y)

            audio = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                                     channels=1, dtype='int16', blocking=True)
            )

            log(f"✓ Recorded {len(audio)} samples", C.G)

            # Notify device we're transcribing
            await self._send({"type": "voice_status", "status": "processing"})

            # Save as WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                import wave as wave_mod
                with wave_mod.open(f.name, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio.tobytes())

            log("Transcribing with Whisper...", C.Y)
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.whisper.transcribe(temp_path, verbose=False)
            )

            text = result["text"].strip()
            os.unlink(temp_path)

            log("━" * 50, C.G if text else C.R)
            if text:
                log(f"VOICE TRANSCRIPTION: \"{text}\"", C.G)
            else:
                log("VOICE TRANSCRIPTION: (empty)", C.R)
            log("━" * 50, C.G if text else C.R)

            # Send result to device
            await self._send({"type": "voice_result", "text": text})

            # If in claude_code mode, also write to command file
            if mode == "claude_code" and text:
                self.current_mode = "claude_code"
                await self._send_to_claude_code(text)

        except Exception as e:
            log(f"✗ Voice recording error: {e}", C.R)
            await self._send({"type": "voice_result", "text": ""})
    
    async def _send_to_claude_api(self, text: str):
        log(f"→ Claude API: \"{text}\"", C.B)
        
        self.conversation.append({"role": "user", "content": text})
        
        headers = {"Content-Type": "application/json"}
        if config.CLAUDE_API_KEY:
            headers["x-api-key"] = config.CLAUDE_API_KEY
            headers["anthropic-version"] = "2023-06-01"
        
        payload = {
            "model": config.CLAUDE_MODEL,
            "max_tokens": 1024,
            "messages": self.conversation[-10:]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                log(f"  POST {config.CLAUDE_ENDPOINT}/v1/messages", C.B)
                resp = await client.post(
                    f"{config.CLAUDE_ENDPOINT}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                log(f"  Response: {resp.status_code}", C.G if resp.status_code == 200 else C.R)
                
                if resp.status_code != 200:
                    log(f"  Error: {resp.text[:300]}", C.R)
                    await self._send({"type": "error", "error": f"API error: {resp.status_code}"})
                    return
                
                data = resp.json()
                response_text = data.get("content", [{}])[0].get("text", "No response")
                
                log("━" * 50, C.G)
                log(f"CLAUDE RESPONSE:", C.BOLD)
                for i in range(0, len(response_text), 70):
                    log(f"  {response_text[i:i+70]}", C.G)
                log("━" * 50, C.G)
                
                self.conversation.append({"role": "assistant", "content": response_text})
                await self._send({"type": "response", "text": response_text})
                
        except Exception as e:
            log(f"✗ API error: {e}", C.R)
            await self._send({"type": "error", "error": str(e)})
    
    async def _send_to_claude_code(self, text: str):
        log("━" * 50, C.H)
        log("CLAUDE CODE VOICE COMMAND", C.BOLD)
        log(f"  \"{text}\"", C.H)
        log("━" * 50, C.H)
        
        cmd_file = Path.home() / ".cardputer_voice_cmd"
        cmd_file.write_text(f"{text}\n#{int(time.time())}")
        log(f"✓ Written to {cmd_file}", C.G)
        
        await self._send({"type": "ack", "text": text})
    
    async def _send(self, msg: dict):
        if self.client and self.client.is_connected:
            data = json.dumps(msg).encode('utf-8')
            log(f"→ SEND: {msg}", C.B)
            try:
                await self.client.write_gatt_char(UART_RX_UUID, data, response=True)
            except Exception as e:
                log(f"✗ Send error: {e}", C.R)
    
    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
    
    async def run_with_reconnect(self):
        """Main loop with auto-reconnect"""
        while self.running:
            # Find and connect to device
            if not self.client or not self.client.is_connected:
                device = await self.scan_for_device()
                if device:
                    try:
                        await self.connect(device)
                        print(f"""
{C.BOLD}{C.G}
{'='*60}
  CONNECTED & READY FOR DEMO!
  
  On Cardputer:
    • Press SPACE to record (6 seconds)
    • Press T for text input mode
    • Press Q to quit app
    
  Auto-reconnect is ENABLED - just restart the app on device
{'='*60}
{C.END}
""")
                    except Exception as e:
                        log(f"Connection failed: {e}", C.R)
                        await asyncio.sleep(2)
                        continue
                else:
                    log("No device found, retrying in 3 seconds...", C.Y)
                    await asyncio.sleep(3)
                    continue
            
            # Wait while connected, check every 500ms
            while self.client and self.client.is_connected:
                await asyncio.sleep(0.5)
            
            # Device disconnected, wait a bit before scanning again
            log("Connection lost, will scan again in 2 seconds...", C.Y)
            self.client = None
            await asyncio.sleep(2)


async def main():
    print(f"""
{C.BOLD}{C.C}
╔═══════════════════════════════════════════════════════════════╗
║               CARDPUTER DEBUG & DEMO TOOL                    ║
║                                                               ║
║  Full visibility into everything happening with your device  ║
║  Auto-reconnect enabled - device can quit & restart          ║
║                                                               ║
║  Audio files saved to: /tmp/cardputer_audio_*.wav            ║
╚═══════════════════════════════════════════════════════════════╝
{C.END}
""")
    
    proxy = DebugProxy()
    
    try:
        await proxy.run_with_reconnect()
    except KeyboardInterrupt:
        print(f"\n{C.Y}Shutting down...{C.END}")
    finally:
        await proxy.disconnect()
        print(f"{C.G}Disconnected.{C.END}")




# ─── HTTP API for Claude Code to send notifications ───
from aiohttp import web

async def handle_notify(request):
    """HTTP endpoint to send notifications to device."""
    try:
        data = await request.json()
        title = data.get('title', 'Notice')
        body = data.get('body', '')
        urgency = data.get('urgency', 'info')
        
        proxy = request.app['proxy']
        if proxy.client and proxy.client.is_connected:
            msg = {"type": "notify", "title": title, "body": body, "urgency": urgency}
            await proxy._send(msg)
            return web.json_response({"ok": True})
        else:
            return web.json_response({"ok": False, "error": "Not connected"}, status=503)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_stats(request):
    """HTTP endpoint to send token stats to device."""
    try:
        data = await request.json()
        tokens = data.get('tokens', 0)

        proxy = request.app['proxy']
        if proxy.client and proxy.client.is_connected:
            msg = {"type": "stats", "tokens": tokens}
            await proxy._send(msg)
            return web.json_response({"ok": True})
        else:
            return web.json_response({"ok": False, "error": "Not connected"}, status=503)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_waiting(request):
    """HTTP endpoint to notify device that Claude is waiting for input."""
    try:
        data = await request.json() if request.can_read_body else {}
        body = data.get('body', 'Waiting for your input...')

        proxy = request.app['proxy']
        if proxy.client and proxy.client.is_connected:
            msg = {"type": "waiting", "body": body}
            await proxy._send(msg)
            return web.json_response({"ok": True})
        else:
            return web.json_response({"ok": False, "error": "Not connected"}, status=503)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_ask(request):
    """HTTP endpoint to send ask questions to device."""
    try:
        data = await request.json()
        question = data.get('question', '?')
        choices = data.get('choices', [])

        proxy = request.app['proxy']
        if proxy.client and proxy.client.is_connected:
            msg = {"type": "ask", "question": question, "choices": choices, "id": str(time.time())}
            await proxy._send(msg)
            # TODO: wait for response
            return web.json_response({"ok": True, "pending": True})
        else:
            return web.json_response({"ok": False, "error": "Not connected"}, status=503)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_voice(request):
    """HTTP endpoint to trigger Mac mic recording and transcription."""
    try:
        data = await request.json() if request.can_read_body else {}
        mode = data.get('mode', 'claude_code')

        proxy = request.app['proxy']
        if proxy.client and proxy.client.is_connected:
            asyncio.create_task(proxy._handle_voice_request(mode))
            return web.json_response({"ok": True, "recording": True})
        else:
            return web.json_response({"ok": False, "error": "Not connected"}, status=503)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def start_http_server(proxy):
    """Start HTTP API server on port 8765."""
    app = web.Application()
    app['proxy'] = proxy
    app.router.add_post('/notify', handle_notify)
    app.router.add_post('/ask', handle_ask)
    app.router.add_post('/stats', handle_stats)
    app.router.add_post('/waiting', handle_waiting)
    app.router.add_post('/voice', handle_voice)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8765)
    await site.start()
    log("HTTP API running on http://localhost:8765", C.G)
    log("  POST /notify  - send notification", C.C)
    log("  POST /stats   - send token stats", C.C)
    log("  POST /waiting - notify Claude is waiting", C.C)
    log("  POST /ask     - send question", C.C)
    log("  POST /voice   - record from Mac mic", C.C)


# Patch main to start HTTP server
_original_main = main

async def main_with_http():
    proxy = DebugProxy()
    
    # Start HTTP server
    await start_http_server(proxy)
    
    print(f"""
{C.BOLD}{C.C}
╔═══════════════════════════════════════════════════════════════╗
║               CARDPUTER DEBUG & DEMO TOOL                    ║
║                                                               ║
║  Full visibility into everything happening with your device  ║
║  Auto-reconnect enabled - device can quit & restart          ║
║                                                               ║
║  HTTP API: http://localhost:8765/notify                      ║
║  Audio files saved to: /tmp/cardputer_audio_*.wav            ║
╚═══════════════════════════════════════════════════════════════╝
{C.END}
""")
    
    try:
        await proxy.run_with_reconnect()
    except KeyboardInterrupt:
        print(f"\n{C.Y}Shutting down...{C.END}")
    finally:
        await proxy.disconnect()
        print(f"{C.G}Disconnected.{C.END}")

main = main_with_http
if __name__ == "__main__":
    asyncio.run(main_with_http())

# ─── Health Reminders (hourly) ───
import random

HEALTH_REMINDERS = [
    ("Hydration Check!", "Time to drink some water"),
    ("Stand Up!", "Stretch your legs, move around"),
    ("Eye Break!", "Look away from screen for 20 sec"),
    ("Posture Check!", "Sit up straight, relax shoulders"),
    ("Deep Breath!", "Take 3 slow deep breaths"),
]

async def _health_reminder_loop(proxy):
    """Send health reminders every hour."""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        if proxy.client and proxy.client.is_connected:
            title, body = random.choice(HEALTH_REMINDERS)
            msg = {"type": "notify", "title": title, "body": body, "urgency": "warn"}
            try:
                await proxy._send(msg)
                log(f"Health reminder sent: {title}", C.G)
            except:
                pass

# Patch main to include health reminders
_prev_main = main

async def main_with_health():
    proxy = DebugProxy()
    await start_http_server(proxy)

    # Start health reminder task
    health_task = asyncio.create_task(_health_reminder_loop(proxy))
    log("Health reminders enabled (every 60 min)", C.G)

    print(f"""
{C.BOLD}{C.C}
╔═══════════════════════════════════════════════════════════════╗
║               CARDPUTER DEBUG & DEMO TOOL                    ║
║                                                               ║
║  Full visibility into everything happening with your device  ║
║  Auto-reconnect enabled - device can quit & restart          ║
║                                                               ║
║  HTTP API: http://localhost:8765/notify                      ║
║  Health reminders: every 60 min                              ║
╚═══════════════════════════════════════════════════════════════╝
{C.END}
""")

    try:
        await proxy.run_with_reconnect()
    except KeyboardInterrupt:
        print(f"\n{C.Y}Shutting down...{C.END}")
    finally:
        health_task.cancel()
        await proxy.disconnect()
        print(f"{C.G}Disconnected.{C.END}")

main = main_with_health
if __name__ == "__main__":
    asyncio.run(main_with_health())
