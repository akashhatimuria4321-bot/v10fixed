# JARVIS OMEGA V11 — Advanced AI Assistant

## What's New in V11

### 🔧 Major Fixes
- **Compound Commands**: "Open YouTube and play latest song" now works as sequential actions
- **Context Awareness**: Remembers last opened app for smart follow-ups
- **Auto-Minimize**: GUI automatically minimizes to a small ball when opening apps/websites
- **Transparent ESC Orb**: ESC minimizes to a 40px transparent ball — no dark background!
- **Space Toggle**: Press SPACE once to start listening, press again to stop
- **No Media Player Window**: TTS plays silently in background without opening any player
- **Faster Responses**: Response caching + fast model priority + pre-warmed calls

### 🧠 Smart Features
- **App Detection**: Checks if Spotify/VLC/etc. are installed before suggesting them
- **USB/Pendrive Scanning**: Detects plugged USB drives and plays audio files
- **Smart Music**: Plays on YouTube if Spotify isn't installed
- **Human-like Logic**: Follows context (e.g., "play a song" after "open YouTube" → plays on YouTube)

### ⚡ Performance
- Response cache for instant repeated commands
- Fast model (phi3) used first, upgrades if needed
- Sequential model calling (no threading bugs)
- Better STT with dynamic noise calibration

## Installation

1. Install Python 3.14.5 from [python.org](https://python.org)
2. Run `install.bat` (double-click)
3. Run `run.bat` to start JARVIS

## Requirements (Python 3.14.5)
All packages are listed in `requirements.txt` and are 3.14 compatible.

## Controls
| Key | Action |
|-----|--------|
| `SPACE` | Toggle voice listening ON/OFF |
| `ESC` | Minimize/restore GUI (transparent ball) |
| `Ctrl+J` | Show chat panel |
| `Ctrl+H` | Hide panels |
| `Ctrl+S` | Quick screenshot |
| `Ctrl+T` | Settings |
| `Ctrl+Q` | Quit |

## Ollama Setup
Install Ollama and pull models:
```bash
ollama pull llama3.2
ollama pull phi3:3.8b
ollama pull qwen3-vl:2b
ollama pull deepseek-coder:1.3b
ollama pull qwen3.5:4b
```

## License
100% FREE — No API Keys Required
