# JARVIS OMEGA V10 — 100% FREE, No API Keys

> Your own Iron Man AI assistant running locally on Windows 11 with Ollama.

## Your Installed Models (from ollama list)
| Role | Model Assigned |
|------|---------------|
| Chat (general) | `llama3.2` |
| Vision (screen) | `qwen3-vl:2b` |
| Code | `deepseek-coder:1.3b` |
| Reasoning | `qwen3-vl:2b` |
| Fast (quick tasks) | `phi3:3.8b` |
| Creative (writing) | `qwen3.5:4b` |

All these are already installed on your system!

## Setup
```
1. Double-click install.bat
2. In a separate terminal: ollama serve
3. Double-click run.bat   OR   python main.py
```

## Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `SPACE` | Toggle voice input (speak to JARVIS) |
| `Ctrl+J` | Show/hide chat panel |
| `Ctrl+O` | Show/hide output panel |
| `Ctrl+S` | Quick screenshot |
| `Ctrl+T` | Settings |
| `ESC` | Minimize to floating J ball |
| `Ctrl+H` | Hide all panels |
| `Ctrl+Q` | Quit |

## What JARVIS Can Do
- **Talk** in Hinglish (Roman script, no Devanagari)
- **Open/close apps** — Chrome, Notepad, Spotify, WhatsApp, etc.
- **Search the web** (DuckDuckGo, no API key)
- **Read your screen** (OCR + vision AI)
- **Control mouse & keyboard** — click, type, hotkeys
- **Take screenshots** → shown in left OUTPUT panel
- **Play music** on Spotify/YouTube
- **System info** — CPU, RAM, disk usage
- **Window management** — focus, resize, move windows
- **Volume control, screen lock**

## Project Structure
```
jarvis_v10/
├── main.py              # Entry point
├── config/
│   └── settings.json    # Model config, user preferences
├── core/
│   └── brain.py         # Multi-model AI engine
├── gui/
│   └── main_window.py   # Full PyQt6 GUI
├── speech/
│   ├── tts_engine.py    # Text-to-speech (Edge TTS + pyttsx3)
│   └── stt_engine.py    # Speech-to-text (Google STT + Whisper)
├── tools/
│   └── automation.py    # PC control (mouse, keyboard, apps)
├── vision/
│   └── screen_vision.py # OCR + Ollama vision model
├── learning/
│   └── trainer.py       # Self-learning memory
├── data/
│   ├── memory.db        # Conversation history
│   └── screenshots/     # Auto-saved screenshots
├── requirements.txt
├── install.bat
└── run.bat
```

## Troubleshooting
| Problem | Fix |
|---------|-----|
| "Ollama connection refused" | Run `ollama serve` in a terminal first |
| TTS not working | `pip install edge-tts pygame` |
| STT not working | `pip install sounddevice SpeechRecognition numpy` |
| Screen read failing | `pip install pytesseract Pillow mss` + install Tesseract OCR |
| Model slow | Use a smaller model — change `chat` to `llama3.2:3b` in settings.json |
