"""
Cardputer Nexus - Local Proxy
Bridges Cardputer to local Whisper + Enterprise Claude

This replaces the Cloudflare Worker for fully local processing.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory for config import
sys.path.insert(0, str(Path(__file__).parent))

try:
    import config
except ImportError:
    print("ERROR: config.py not found. Copy config.example.py to config.py and edit.")
    sys.exit(1)

# Optional imports based on config
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nexus-proxy")

# =============================================================================
# SPEECH-TO-TEXT BACKENDS
# =============================================================================

class WhisperLocalSTT:
    """Local Whisper speech-to-text"""

    def __init__(self):
        if not WHISPER_AVAILABLE:
            raise ImportError("whisper not installed. Run: pip install openai-whisper")

        logger.info(f"Loading Whisper model: {config.WHISPER_MODEL}")
        self.model = whisper.load_model(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE
        )
        logger.info("Whisper model loaded")

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio bytes to text"""
        # Write to temp file (whisper expects file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            # Run in thread pool to not block async loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(temp_path)
            )
            return result["text"].strip()
        finally:
            os.unlink(temp_path)


class MacOSNativeSTT:
    """macOS native speech recognition (placeholder)"""

    def __init__(self):
        if sys.platform != "darwin":
            raise RuntimeError("macOS native STT only available on macOS")
        logger.info("Using macOS native speech recognition")

    async def transcribe(self, audio_data: bytes) -> str:
        raise NotImplementedError(
            "macOS native STT requires PyObjC. Use whisper_local instead."
        )


def get_stt_backend():
    """Factory function for STT backend"""
    backend = config.STT_BACKEND

    if backend == "whisper_local":
        return WhisperLocalSTT()
    elif backend == "macos_native":
        return MacOSNativeSTT()
    else:
        raise ValueError(f"Unknown STT backend: {backend}")


# =============================================================================
# CLAUDE CLIENT
# =============================================================================

class ClaudeClient:
    """Client for enterprise Claude endpoint"""

    def __init__(self):
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx not installed. Run: pip install httpx")

        self.endpoint = config.CLAUDE_ENDPOINT
        self.model = config.CLAUDE_MODEL
        self.api_key = config.CLAUDE_API_KEY

        logger.info(f"Claude endpoint: {self.endpoint}")
        logger.info(f"Claude model: {self.model}")

    async def chat(self, message: str, conversation_history: list = None) -> str:
        """Send message to Claude and get response"""

        messages = conversation_history or []
        messages.append({"role": "user", "content": message})

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": messages
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/messages",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()

            data = response.json()

            if "content" in data and len(data["content"]) > 0:
                return data["content"][0]["text"]

            return "No response from Claude"


# =============================================================================
# BLE BRIDGE
# =============================================================================

UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
UART_RX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


class NexusBLEBridge:
    """BLE bridge between Cardputer and local services"""

    def __init__(self, stt, claude):
        if not BLEAK_AVAILABLE:
            raise ImportError("bleak not installed. Run: pip install bleak")

        self.stt = stt
        self.claude = claude
        self.client = None
        self.conversation_history = []
        self.audio_buffer = bytearray()

    async def scan_for_device(self):
        """Scan for Nexus device"""
        logger.info("Scanning for Nexus device...")

        devices = await BleakScanner.discover()

        for device in devices:
            name = device.name or ""
            if name.startswith("Nexus-") or name.startswith("Claude-"):
                logger.info(f"Found device: {name} ({device.address})")
                return device

        return None

    async def connect(self, device):
        """Connect to device"""
        logger.info(f"Connecting to {device.name}...")

        self.client = BleakClient(device.address)
        await self.client.connect()

        logger.info("Connected!")
        await self.client.start_notify(UART_RX_UUID, self._on_receive)

    async def _on_receive(self, sender, data: bytearray):
        """Handle data received from Cardputer"""
        try:
            message = json.loads(data.decode('utf-8'))
            await self._handle_message(message)
        except json.JSONDecodeError:
            self.audio_buffer.extend(data)

    async def _handle_message(self, message: dict):
        """Handle parsed message from device"""
        msg_type = message.get("type")

        if msg_type == "audio_start":
            self.audio_buffer = bytearray()
            logger.info("Audio recording started")

        elif msg_type == "audio_end":
            logger.info(f"Audio recording ended, {len(self.audio_buffer)} bytes")
            await self._process_audio()

        elif msg_type == "text":
            text = message.get("content", "")
            await self._process_text(text)

        elif msg_type == "ping":
            await self._send({"type": "pong"})

    async def _process_audio(self):
        """Process recorded audio"""
        if len(self.audio_buffer) == 0:
            logger.warning("Empty audio buffer")
            return

        await self._send({"type": "status", "status": "transcribing"})

        try:
            text = await self.stt.transcribe(bytes(self.audio_buffer))
            logger.info(f"Transcribed: {text}")

            if text:
                await self._send({"type": "transcription", "text": text})
                await self._process_text(text)
            else:
                await self._send({"type": "error", "error": "Could not transcribe audio"})

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            await self._send({"type": "error", "error": str(e)})

    async def _process_text(self, text: str):
        """Send text to Claude and return response"""
        await self._send({"type": "status", "status": "thinking"})

        try:
            response = await self.claude.chat(text, self.conversation_history)

            self.conversation_history.append({"role": "user", "content": text})
            self.conversation_history.append({"role": "assistant", "content": response})

            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            await self._send({"type": "response", "text": response})
            logger.info(f"Response: {response[:100]}...")

        except Exception as e:
            logger.error(f"Claude error: {e}")
            await self._send({"type": "error", "error": str(e)})

    async def _send(self, message: dict):
        """Send message to device"""
        if self.client and self.client.is_connected:
            data = json.dumps(message).encode('utf-8')
            await self.client.write_gatt_char(UART_TX_UUID, data)

    async def disconnect(self):
        """Disconnect from device"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║         CARDPUTER NEXUS - LOCAL PROXY     ║
    ║                                           ║
    ║  Voice AI + Enterprise Claude Bridge      ║
    ╚═══════════════════════════════════════════╝
    """)

    logger.info("Initializing speech-to-text...")
    stt = get_stt_backend()

    logger.info("Initializing Claude client...")
    claude = ClaudeClient()

    bridge = NexusBLEBridge(stt, claude)

    device = await bridge.scan_for_device()

    if not device:
        logger.error("No Nexus device found. Make sure device is powered on.")
        return

    await bridge.connect(device)

    print("\nProxy running. Press Ctrl+C to exit.\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await bridge.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
