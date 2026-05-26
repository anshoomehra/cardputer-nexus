# Cardputer Nexus - Local Configuration
# Copy this file to config.py and edit with your settings

# =============================================================================
# ENTERPRISE CLAUDE ENDPOINT
# =============================================================================

# Your enterprise Claude endpoint (e.g., localhost proxy, Azure, AWS Bedrock)
CLAUDE_ENDPOINT = "http://localhost:9999"

# Model to use (must be available at your endpoint)
CLAUDE_MODEL = "claude-opus-4-6"

# API key (if required by your endpoint)
# Leave empty if using a proxy that handles auth
CLAUDE_API_KEY = ""

# =============================================================================
# SPEECH-TO-TEXT CONFIGURATION
# =============================================================================

# STT backend: "whisper_local" | "whisper_api" | "macos_native"
STT_BACKEND = "whisper_local"

# Local Whisper settings (if STT_BACKEND = "whisper_local")
WHISPER_MODEL = "base"  # tiny | base | small | medium | large
WHISPER_DEVICE = "cpu"  # cpu | cuda | mps (Apple Silicon)

# Whisper API settings (if STT_BACKEND = "whisper_api")
WHISPER_API_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
WHISPER_API_KEY = ""

# =============================================================================
# DEVICE SETTINGS
# =============================================================================

# Unique device identifier (auto-generated if empty)
DEVICE_ID = ""

# Device display name (shown in Claude Hardware Buddy)
DEVICE_NAME = "Nexus"

# WiFi credentials for auto-connect on boot
WIFI_SSID = ""
WIFI_PASSWORD = ""

# =============================================================================
# MCP SERVER SETTINGS
# =============================================================================

# Enable/disable specific MCP tools
MCP_ENABLE_NOTIFY = True
MCP_ENABLE_ASK = True
MCP_ENABLE_CONFIRM = True

# Confirm tool settings
CONFIRM_HOLD_DURATION_MS = 2000  # How long to hold Y key
CONFIRM_DEFAULT_TIMEOUT_S = 60

# =============================================================================
# CLOUDFLARE WORKER (OPTIONAL)
# =============================================================================

# Only needed if using cloud-based voice processing
# Leave empty to use local processing

WORKER_BASE = ""  # e.g., "https://nexus.your-domain.workers.dev"
DEVICE_SECRET = ""  # Shared secret for device authentication

# =============================================================================
# MANAGED AGENTS / PAGER SETTINGS
# =============================================================================

# Enable Claude Pager functionality
PAGER_ENABLED = True

# Daily spawn cap for Managed Agents (cost control)
PAGER_DAILY_SPAWN_CAP = 30

# Notification sounds
PAGER_SOUND_COMPLETE = True
PAGER_SOUND_PENDING = True
PAGER_SOUND_FAILED = True

# =============================================================================
# PET / COMPANION SETTINGS (COMING SOON)
# =============================================================================

# Default pet species (see README for full list)
DEFAULT_PET = "capybara"

# Enable pet mood system
PET_MOOD_ENABLED = True

# Enable sound effects
PET_SOUNDS_ENABLED = True

# Enable RGB LED effects
PET_LED_ENABLED = True

# =============================================================================
# LOGGING / DEBUG
# =============================================================================

# Log level: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL = "INFO"

# Log to SD card
LOG_TO_SD = False

# Remote logging webhook (for enterprise auditing)
LOG_WEBHOOK_URL = ""

# =============================================================================
# ENTERPRISE / FLEET SETTINGS
# =============================================================================

# Organization identifier
ORG_ID = ""

# Fleet management server (for OTA updates, config sync)
FLEET_SERVER = ""

# Device attestation key (for enterprise compliance)
ATTESTATION_KEY = ""
