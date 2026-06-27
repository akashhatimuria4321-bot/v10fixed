"""
main.py — JARVIS OMEGA V10
100% FREE — No API Keys — Multi-Model Ollama Architecture
Python 3.14.5 | Windows 11
"""
from __future__ import annotations
import sys
import os
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# ── Load Settings ──────────────────────────────────────────────────────────────
def _load_settings() -> dict:
    path = BASE / "config" / "settings.json"
    try:
        s = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("[MAIN] settings.json not found, using defaults")
        s = {}
    except json.JSONDecodeError as e:
        print(f"[MAIN] settings.json parse error: {e}")
        s = {}

    s.setdefault("user_name", "Sir")
    s.setdefault("ai_name", "JARVIS")
    s.setdefault("tts_voice", "en-IN-PrabhatNeural")
    s.setdefault("tts_edge_rate", "+5%")
    s.setdefault("tts_edge_pitch", "+0Hz")
    s.setdefault("tts_rate", 185)
    s.setdefault("hinglish_display_mode", True)
    s.setdefault("hinglish_speak_mode", True)
    s.setdefault("hindi_speak_mode", False)
    s.setdefault("stt_language", "hi-en")
    s.setdefault("stt_fallback_langs", ["hi-IN", "en-IN", "en-US"])
    s.setdefault("whisper_model", "base")
    s.setdefault("offline_mode", True)
    s.setdefault("ollama_url", "http://localhost:11434")

    s.setdefault("V10_MODELS", {})
    s["V10_MODELS"].setdefault("chat", "llama3.2")
    s["V10_MODELS"].setdefault("vision", "qwen3-vl:2b")
    s["V10_MODELS"].setdefault("code", "deepseek-coder:1.3b")
    s["V10_MODELS"].setdefault("reasoning", "qwen3-vl:2b")
    s["V10_MODELS"].setdefault("fast", "phi3:3.8b")
    s["V10_MODELS"].setdefault("creative", "qwen3.5:4b")

    s.setdefault("V10_FEATURES", {})
    s["V10_FEATURES"].setdefault("computer_control_enabled", True)
    s["V10_FEATURES"].setdefault("vision_enabled", True)
    s["V10_FEATURES"].setdefault("learning_enabled", True)
    s["V10_FEATURES"].setdefault("web_search_enabled", True)
    s["V10_FEATURES"].setdefault("esc_orb_mode", False)
    s["V10_FEATURES"].setdefault("esc_orb_size", 120)

    return s


# ── Qt High-DPI ────────────────────────────────────────────────────────────────
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


# ── Start ──────────────────────────────────────────────────────────────────────
def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS OMEGA V10")
    app.setQuitOnLastWindowClosed(False)

    settings = _load_settings()

    print("[MAIN] 🚀 JARVIS OMEGA V10 Starting...")
    print("[MAIN] 💰 100% FREE — No API Keys Required")
    print(f"[MAIN] 🧠 Ollama @ {settings['ollama_url']}")
    print(f"[MAIN] 📦 Models: {settings['V10_MODELS']}")

    from gui.main_window import JarvisOmegaWindow
    win = JarvisOmegaWindow(settings)
    win.show()

    print("[MAIN] ✅ JARVIS OMEGA V10 Ready — Press SPACE to speak")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
