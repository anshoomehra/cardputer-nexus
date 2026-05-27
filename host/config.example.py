# Cardputer Nexus - Configuration
# Copy this file to config.py and edit with your settings

# =============================================================================
# CLAUDE API CONFIGURATION
# =============================================================================

# Option 1: Use Anthropic API directly (recommended for most users)
# Get your API key from: https://console.anthropic.com/
CLAUDE_ENDPOINT = "https://api.anthropic.com"
CLAUDE_API_KEY = ""  # Your Anthropic API key: sk-ant-...
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Option 2: Use a local/enterprise endpoint (no API key needed)
# Uncomment these and comment out Option 1 above:
# CLAUDE_ENDPOINT = "http://localhost:9999"
# CLAUDE_API_KEY = ""
# CLAUDE_MODEL = "claude-sonnet-4-20250514"

# =============================================================================
# SPEECH-TO-TEXT CONFIGURATION
# =============================================================================

# STT backend: "whisper_local" | "whisper_api" | "macos_native"
STT_BACKEND = "whisper_local"

# Local Whisper settings (if STT_BACKEND = "whisper_local")
WHISPER_MODEL = "base"  # tiny | base | small | medium | large
WHISPER_DEVICE = "cpu"  # cpu | cuda | mps (Apple Silicon)

# =============================================================================
# DEVICE SETTINGS
# =============================================================================

# Device display name
DEVICE_NAME = "Nexus"
