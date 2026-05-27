"""Claude Nexus — Unified companion with pets, sounds, and stats"""

import gc
import json
import time

import M5
import machine
from hardware import MatrixKeyboard

_BLACK = 0x000000
_ORANGE = 0xCC785C
_CREAM = 0xF0EEE6
_DARK = 0x1F1F1F
_GRAY = 0x777777
_GREEN = 0x00FF00
_RED = 0xFF0000
_CYAN = 0x00DDDD
_YELLOW = 0xFFFF00
_BLUE = 0x4488FF
_PINK = 0xFF88CC

_LCD = M5.Lcd
_W = 240
_H = 135

_NUS_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
_NUS_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
_NUS_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

_FLAG_READ = 0x0002
_FLAG_WRITE_NR = 0x0004
_FLAG_WRITE = 0x0008
_FLAG_NOTIFY = 0x0010

# ─── PET DEFINITIONS ───
# Cat
CAT_IDLE = ["   /\\_/\\   ", "  ( o.o )  ", "   > ^ <   ", "  (\")_(\") "]
CAT_HAPPY = ["   /\\_/\\   ", "  ( ^.^ )  ", "   > W <   ", " ~(\")_(\")~"]
CAT_ALERT = ["   /!_!\\   ", "  ( O.O )  ", "   > ! <   ", "  (\")_(\") "]
CAT_SLEEP = ["   /\\_/\\   ", "  ( -.- ) z", "   > ~ <  Z", "  (\")_(\") "]

# Dog (with tail wag frames)
DOG_IDLE = ["  __      _", " /  \\__/|\\|", "(  o.o   )/", " \\__U__/| |"]
DOG_WAG1 = ["  __      _", " /  \\__/|/|", "(  ^.^   ) ", " \\__U__/|\\ "]
DOG_WAG2 = ["  __      _", " /  \\__/|\\|", "(  ^.^   ) ", " \\__U__/|/ "]
DOG_ALERT = ["  __    !!_", " /  \\__/|\\|", "(  O.O   )!", " \\__U__/| |"]
DOG_SLEEP = ["  __      _", " /  \\__/|.|", "(  -.-  z) ", " \\__U__/|Z|"]

# Blob
BLOB_IDLE = ["   .-\"\"\"-. ", "  /  o o  \\", " |    ~    |", "  \\_______/"]
BLOB_HAPPY = ["  \\.-\"\"\"-./", "   / ^.^ \\ ", "  |   W   | ", "   \\_____/ "]
BLOB_ALERT = ["   .-!!-. ", "  /  O O  \\", " |    !    |", "  \\_______/"]
BLOB_SLEEP = ["   .-\"\"\"-. ", "  /  - -  \\", " |  z ~ z  |", "  \\_______/"]

# Bunny
BUNNY_IDLE = ["  (\\(\\ ", "  ( -.-)  ", "  o_(\")(\")"]
BUNNY_HAPPY = ["  (\\(\\    ", "  ( ^.^)~ ", "  o_(\")(\")"]
BUNNY_ALERT = ["  /|/|    ", "  (O.O )! ", "  o_(\")(\")"]

PETS = {
    "cat": {"idle": CAT_IDLE, "happy": CAT_HAPPY, "alert": CAT_ALERT, "sleep": CAT_SLEEP, "color": 0xC2A6},
    "dog": {"idle": DOG_IDLE, "wag1": DOG_WAG1, "wag2": DOG_WAG2, "alert": DOG_ALERT, "sleep": DOG_SLEEP, "color": 0xDDAA55},
    "blob": {"idle": BLOB_IDLE, "happy": BLOB_HAPPY, "alert": BLOB_ALERT, "sleep": BLOB_SLEEP, "color": 0x88CCFF},
    "bunny": {"idle": BUNNY_IDLE, "happy": BUNNY_HAPPY, "alert": BUNNY_ALERT, "sleep": BUNNY_IDLE, "color": 0xFFCCDD},
}

_current_pet = "cat"
_pet_names = list(PETS.keys())

_ble = None
_tx_handle = None
_conn_handle = None
_connected = False
_inbox = []

# Stats tracking
_total_tokens = 0
_last_activity = 0
_idle_alert_sent = False
_IDLE_THRESHOLD_MS = 300000  # 5 minutes

def _set_font():
    try:
        _LCD.setFont(_LCD.FONTS.DejaVu9)
    except:
        pass

def _beep(urgency="info"):
    """Play sound based on urgency level."""
    try:
        spk = M5.Speaker
        spk.setVolume(255)  # Max volume
        if urgency == "crit":
            for f in (660, 880, 660):
                spk.tone(f, 80)
                time.sleep_ms(40)
        elif urgency == "warn":
            spk.tone(660, 100)
            time.sleep_ms(60)
            spk.tone(880, 100)
        elif urgency == "happy":
            spk.tone(880, 80)
            time.sleep_ms(40)
            spk.tone(1320, 120)
        else:  # info
            spk.tone(880, 60)
    except:
        pass

def _beep_idle():
    """Gentle reminder beep."""
    try:
        spk = M5.Speaker
        spk.setVolume(200)  # Slightly lower for idle
        spk.tone(440, 50)
        time.sleep_ms(100)
        spk.tone(440, 50)
    except:
        pass

def _draw_pet(mood="idle", y_start=40):
    pet = PETS[_current_pet]
    frames = pet.get(mood, pet["idle"])
    color = pet["color"]
    _LCD.setTextColor(color, _BLACK)
    for i, line in enumerate(frames):
        x = (_W - len(line) * 6) // 2
        _LCD.drawString(line, x, y_start + i * 12)

def _draw_stats():
    """Draw token usage in top bar."""
    if _total_tokens > 0:
        if _total_tokens >= 1000000:
            tok_str = "{:.1f}M".format(_total_tokens / 1000000)
        elif _total_tokens >= 1000:
            tok_str = "{:.1f}K".format(_total_tokens / 1000)
        else:
            tok_str = str(_total_tokens)
        _LCD.setTextColor(_BLUE, _DARK)
        _LCD.drawString(tok_str, 100, 5)

def _draw_main():
    global _idle_alert_sent
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)
    _LCD.fillRect(0, 20, _W, 1, _ORANGE)
    _LCD.setTextColor(_ORANGE, _DARK)
    _LCD.drawString("Claude Nexus", 6, 5)

    _draw_stats()

    color = _GREEN if _connected else _RED
    status = "LINKED" if _connected else "OFFLINE"
    _LCD.setTextColor(color, _DARK)
    _LCD.drawString(status, _W - _LCD.textWidth(status) - 6, 5)

    _draw_pet("idle")

    _LCD.fillRect(0, _H - 18, _W, 18, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("T txt V voice P pet Q quit", 30, _H - 14)

    _idle_alert_sent = False

def _draw_notify(title, body, urgency="info"):
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)

    if urgency == "crit":
        _LCD.setTextColor(_RED, _DARK)
    elif urgency == "warn":
        _LCD.setTextColor(_YELLOW, _DARK)
    else:
        _LCD.setTextColor(_CYAN, _DARK)
    _LCD.drawString("NOTIFICATION", 6, 5)

    _draw_stats()

    _draw_pet("alert", 22)

    _LCD.setTextColor(_YELLOW, _BLACK)
    title_x = max(10, (_W - len(title[:30]) * 6) // 2)
    _LCD.drawString(title[:30], title_x, 75)

    _LCD.setTextColor(_CREAM, _BLACK)
    body_x = max(10, (_W - len(body[:38]) * 6) // 2)
    _LCD.drawString(body[:38], body_x, 90)

    _LCD.fillRect(0, _H - 15, _W, 15, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("SPACE dismiss", 75, _H - 12)


    _beep(urgency)

# Global to store current ask context
_ask_id = None
_ask_choices = []

def _draw_ask(question, choices):
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)
    _LCD.setTextColor(_YELLOW, _DARK)
    _LCD.drawString("ACTION NEEDED", 6, 5)

    _draw_stats()

    _draw_pet("alert", 22)

    # Question
    _LCD.setTextColor(_CREAM, _BLACK)
    q_x = max(10, (_W - len(question[:35]) * 6) // 2)
    _LCD.drawString(question[:35], q_x, 72)

    # Choices (up to 4)
    _LCD.setTextColor(_CYAN, _BLACK)
    y = 88
    for i, choice in enumerate(choices[:4]):
        choice_text = f"{i+1}={choice[:12]}"
        _LCD.drawString(choice_text, 10 + (i % 2) * 115, y + (i // 2) * 14)

    _LCD.fillRect(0, _H - 15, _W, 15, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("Press 1-4 to choose", 60, _H - 12)

    _beep("warn")

def _draw_text_input(text, cursor):
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)
    _LCD.setTextColor(_CYAN, _DARK)
    _LCD.drawString("Type command:", 6, 5)
    _draw_stats()

    _LCD.fillRect(5, 30, _W - 10, 70, _DARK)
    _LCD.setTextColor(_CREAM, _DARK)
    display = text[-30:] + ("|" if cursor else " ")
    _LCD.drawString(display, 10, 50)

    _LCD.fillRect(0, _H - 18, _W, 18, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("ENTER send  ESC cancel", 40, _H - 14)

def _draw_voice(status="listening"):
    """Show voice mode screen."""
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)
    _LCD.setTextColor(_PINK, _DARK)
    _LCD.drawString("VOICE MODE", 6, 5)
    _draw_stats()
    _draw_pet("alert", 22)
    _LCD.setTextColor(_CREAM, _BLACK)
    if status == "listening":
        _LCD.drawString("Listening on Mac mic...", 45, 80)
    elif status == "recording":
        _LCD.drawString("Recording from device...", 40, 80)
    elif status == "processing":
        _LCD.drawString("Transcribing...", 70, 80)
    _LCD.fillRect(0, _H - 15, _W, 15, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("ESC cancel", 80, _H - 12)
    _beep("info")

def _draw_sent(text):
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)
    _LCD.setTextColor(_GREEN, _DARK)
    _LCD.drawString("SENT!", 6, 5)
    _draw_stats()

    _draw_pet("happy")

    _LCD.setTextColor(_CREAM, _BLACK)
    _LCD.drawString(text[:35], 10, 100)

    _LCD.fillRect(0, _H - 18, _W, 18, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("T again  Q quit", 75, _H - 14)

    _beep("happy")

def _draw_idle_alert():
    """Show idle status with sleeping pet."""
    _LCD.fillScreen(_BLACK)
    _LCD.fillRect(0, 0, _W, 20, _DARK)
    _LCD.setTextColor(_YELLOW, _DARK)
    _LCD.drawString("IDLE", 6, 5)
    _draw_stats()

    color = _GREEN if _connected else _RED
    status = "LINKED" if _connected else "OFFLINE"
    _LCD.setTextColor(color, _DARK)
    _LCD.drawString(status, _W - _LCD.textWidth(status) - 6, 5)

    _draw_pet("sleep", 25)

    _LCD.setTextColor(_GRAY, _BLACK)
    _LCD.drawString("No activity for 5 min", 55, 80)
    _LCD.setTextColor(_CYAN, _BLACK)
    _LCD.drawString("Press any key to wake up!", 40, 95)

    _LCD.fillRect(0, _H - 18, _W, 18, _DARK)
    _LCD.setTextColor(_GRAY, _DARK)
    _LCD.drawString("T txt V voice P pet Q quit", 30, _H - 14)

    _beep_idle()

def _cycle_pet():
    global _current_pet
    idx = _pet_names.index(_current_pet)
    _current_pet = _pet_names[(idx + 1) % len(_pet_names)]
    _beep("info")

def _ble_irq(event, data):
    global _connected, _conn_handle

    if event == 1:
        _conn_handle = data[0]
        _connected = True
    elif event == 2:
        _conn_handle = None
        _connected = False
        _start_adv()
    elif event == 3:
        conn, attr = data
        value = _ble.gatts_read(attr)
        try:
            msg = json.loads(value.decode())
            _inbox.append(msg)
        except:
            pass

def _setup_ble():
    global _ble, _tx_handle
    import bluetooth

    _ble = bluetooth.BLE()
    _ble.active(True)
    _ble.irq(_ble_irq)

    mac = _ble.config("mac")[1]
    name = "ClaudeNexus_{:02X}{:02X}{:02X}".format(mac[3], mac[4], mac[5])
    _ble.config(gap_name=name)

    NUS = bluetooth.UUID(_NUS_UUID)
    NUS_RX = bluetooth.UUID(_NUS_RX_UUID)
    NUS_TX = bluetooth.UUID(_NUS_TX_UUID)

    svc = (NUS, ((NUS_RX, _FLAG_WRITE | _FLAG_WRITE_NR), (NUS_TX, _FLAG_READ | _FLAG_NOTIFY)))
    handles = _ble.gatts_register_services((svc,))
    _rx_handle = handles[0][0]
    _tx_handle = handles[0][1]
    _ble.gatts_set_buffer(_rx_handle, 512, True)
    _ble.gatts_set_buffer(_tx_handle, 512, True)

    _start_adv()

def _start_adv():
    if not _ble:
        return
    name = _ble.config("gap_name")
    if isinstance(name, str):
        name = name.encode()
    _ble.gap_advertise(100_000, bytes([2, 1, 6]) + bytes([len(name) + 1, 9]) + name)

def _send(msg):
    if _connected and _conn_handle and _tx_handle:
        try:
            _ble.gatts_notify(_conn_handle, _tx_handle, json.dumps(msg).encode())
            return True
        except:
            pass
    return False

def _get_text(kb):
    text = ""
    cursor = True
    last_blink = time.ticks_ms()
    _draw_text_input(text, cursor)

    while True:
        kb.tick()
        k = kb.get_key()

        if k in (0x0D, 0x0A, '\n', '\r'):
            return text if text else None
        elif k in ('q', 'Q', 0x1B, 0x71, 0x51):
            return None
        elif k in (0x08, 127):
            text = text[:-1]
        elif isinstance(k, str) and len(k) == 1 and 0x20 <= ord(k) <= 0x7E:
            if len(text) < 100:
                text += k
        elif isinstance(k, int) and 0x20 <= k <= 0x7E:
            if len(text) < 100:
                text += chr(k)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_blink) > 500:
            cursor = not cursor
            last_blink = now
            _draw_text_input(text, cursor)

        time.sleep_ms(50)

def run():
    global _inbox, _total_tokens, _last_activity, _idle_alert_sent

    M5.begin()
    _set_font()
    gc.collect()

    _setup_ble()
    _last_activity = time.ticks_ms()
    _draw_main()

    time.sleep_ms(800)
    kb = MatrixKeyboard()
    time.sleep_ms(400)

    state = "idle"
    last_redraw = time.ticks_ms()
    anim_frame = 0

    try:
        while True:
            kb.tick()
            k = kb.get_key()

            if k in ('q', 'Q', 0x71, 0x51):
                break

            now = time.ticks_ms()

            # Check inbox FIRST
            if _inbox:
                msg = _inbox.pop(0)
                msg_type = msg.get("type", "")
                _last_activity = now
                _idle_alert_sent = False

                if msg_type == "notify":
                    urgency = msg.get("urgency", "info")
                    _draw_notify(msg.get("title", "Notice"), msg.get("body", ""), urgency)
                    state = "notify"
                    last_redraw = now
                    continue
                elif msg_type == "stats":
                    _total_tokens = msg.get("tokens", _total_tokens)
                    if state == "idle":
                        _draw_main()
                        last_redraw = now
                    continue
                elif msg_type == "waiting":
                    # Claude is waiting for user input
                    _draw_notify("Claude Waiting", msg.get("body", "Ready for your input"), "warn")
                    state = "notify"
                    last_redraw = now
                    continue
                elif msg_type == "ask":
                    global _ask_id, _ask_choices
                    _ask_id = msg.get("id", "")
                    _ask_choices = msg.get("choices", [])
                    _draw_ask(msg.get("question", "?"), _ask_choices)
                    state = "ask"
                    last_redraw = now
                    continue
                elif msg_type == "voice_result":
                    text = msg.get("text", "")
                    if text:
                        _draw_sent("Voice: " + text[:25])
                    else:
                        _draw_sent("No speech detected")
                    state = "sent"
                    last_redraw = now
                    continue
                elif msg_type == "voice_status":
                    if state == "voice":
                        _draw_voice(msg.get("status", "processing"))
                        last_redraw = now
                    continue
                elif msg_type in ("ack", "response"):
                    _draw_sent(msg.get("text", "OK"))
                    state = "sent"
                    last_redraw = now
                    continue
                elif msg_type == "error":
                    _draw_sent("Error: " + msg.get("error", "")[:20])
                    state = "sent"
                    last_redraw = now
                    continue

            # Pet cycling with P key
            if k in ('p', 'P', 0x70, 0x50):
                _cycle_pet()
                _last_activity = now
                if state == "idle":
                    _draw_main()
                    last_redraw = now

            # State handling
            if state == "idle":
                # Check for idle timeout
                if not _idle_alert_sent and time.ticks_diff(now, _last_activity) > _IDLE_THRESHOLD_MS:
                    _draw_idle_alert()
                    _idle_alert_sent = True
                    last_redraw = now
                elif time.ticks_diff(now, last_redraw) > 3000:
                    _draw_main()
                    last_redraw = now

                if k in ('t', 'T', ' ', 0x74, 0x54, 0x20):
                    _last_activity = now
                    if _idle_alert_sent:
                        # Just wake up from sleep, don't open text mode
                        _idle_alert_sent = False
                        _draw_main()
                        last_redraw = now
                    else:
                        # Normal: open text input
                        text = _get_text(kb)
                        if text:
                            _send({"type": "text", "content": text, "mode": "claude_code"})
                            _draw_main()
                            _LCD.setTextColor(_CYAN, _BLACK)
                            _LCD.drawString("Sending...", 85, 100)
                            state = "waiting"
                            last_redraw = now
                        else:
                            _draw_main()
                            last_redraw = now

                if k in ('v', 'V', 0x76, 0x56):
                    _last_activity = now
                    if _idle_alert_sent:
                        _idle_alert_sent = False
                        _draw_main()
                        last_redraw = now
                    else:
                        # V = Mac mic recording via host
                        _draw_voice("listening")
                        _send({"type": "voice_request", "mode": "claude_code"})
                        state = "voice"
                        last_redraw = now

            elif state == "voice":
                # Waiting for voice transcription result
                if time.ticks_diff(now, last_redraw) > 30000:
                    _draw_main()
                    state = "idle"
                    last_redraw = now
                elif k in (0x1B,):
                    _draw_main()
                    state = "idle"
                    last_redraw = now

            elif state == "waiting":
                # Dog tail wag animation while waiting
                if _current_pet == "dog" and time.ticks_diff(now, last_redraw) > 300:
                    anim_frame = (anim_frame + 1) % 2
                    mood = "wag1" if anim_frame == 0 else "wag2"
                    _LCD.fillRect(0, 40, _W, 60, _BLACK)
                    _draw_pet(mood)
                    last_redraw = now

                if time.ticks_diff(now, _last_activity) > 15000:
                    _draw_main()
                    state = "idle"
                    last_redraw = now

            elif state == "ask":
                # Handle number key presses for choices
                choice = None
                if k in ('1', 0x31):
                    choice = 0
                elif k in ('2', 0x32):
                    choice = 1
                elif k in ('3', 0x33):
                    choice = 2
                elif k in ('4', 0x34):
                    choice = 3
                
                if choice is not None and choice < len(_ask_choices):
                    _send({"type": "ask_response", "id": _ask_id, "choice": choice, "value": _ask_choices[choice]})
                    _draw_sent(f"Selected: {_ask_choices[choice]}")
                    state = "sent"
                    last_redraw = now

            elif state in ("notify", "sent"):
                # Auto-dismiss after 30 seconds
                if time.ticks_diff(now, last_redraw) > 30000:
                    _draw_main()
                    state = "idle"
                    last_redraw = now
                elif k in (' ', 0x20, 't', 'T', 0x74, 0x54):
                    _last_activity = now
                    _draw_main()
                    state = "idle"
                    last_redraw = now

            time.sleep_ms(50)

    finally:
        if _ble:
            _ble.active(False)
        machine.reset()

run()
