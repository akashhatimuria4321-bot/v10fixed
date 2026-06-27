# JARVIS V10 — What Was Fixed

## 🔴 Root Cause: "All models timeout"

The `race()` function used `concurrent.futures.ThreadPoolExecutor` with lambda closures.
Two bugs combined to make every call return `None`:

1. **`future.result(timeout=0)`** — This raised `TimeoutError` immediately for any model
   that hadn't finished in 0ms. Every model "timed out" instantly.

2. **Lambda closure bug** — The lambdas inside `build_chat_callers()` captured `fn`
   by reference (not value), so all closures pointed to the same (last) function.

**Fix:** Replaced `race()` with `call_first_available()` — tries each model
sequentially. First non-empty response wins. No threads, no closures, no race conditions.

---

## 🔴 Ollama Timeouts Too Short

- `timeout=(3, 30)` — 3s connect, 30s read
- Cold model load (first call after `ollama serve`) can take 20-60s
- Phi3 and larger models can take 15-40s to generate a response

**Fix:** `timeout=(8, 120)` — 8s connect, 120s read.

---

## 🔴 TTS Broken on Python 3.14

- `pygame` — uses deprecated `imp` module, crashes Python 3.14
- `playsound` — also uses deprecated `imp`, crashes Python 3.14

**Fix:** Removed both. Audio now plays via:
- WAV files → `winsound` (built-in Python, no install needed)
- MP3 files → PowerShell `System.Windows.Media.MediaPlayer` (built-in Windows)
- Fallback → `wmplayer` (built-in Windows)
- pyttsx3 still works as offline TTS (no audio file needed)

---

## 🔴 STT Required Groq API Key

The old code checked for `groq_api_key` and printed warnings when missing.
Google STT (free, no key) was only used as a third fallback.

**Fix:** 
- Removed Groq entirely (it was the only thing that needed an API key)
- Google STT (via `SpeechRecognition` library) is now **primary** — free, no key
- Local Whisper stays as offline fallback

---

## 🟡 Other Fixes

| Issue | Fix |
|-------|-----|
| `reasoning` model set to `qwen3-vl:2b` (slow vision model) | Changed to `llama3.2` (fast chat) |
| Web search triggered on greetings, adding latency | Tighter `needs_search()` guard |
| No startup Ollama check | Added `check_ollama_running()` with clear instructions |
| Model not installed = silent timeout | Added `_validate_models()` with `ollama pull` hints |

---

## ✅ How to Run

```
1. Terminal 1:   ollama serve
2. Terminal 2:   python main.py   (or double-click run.bat)
```

## ✅ Python 3.14 Safe Packages

| Package | Status |
|---------|--------|
| PyQt6 | ✅ Works |
| requests | ✅ Works |
| sounddevice + numpy | ✅ Works (replaces PyAudio) |
| SpeechRecognition | ✅ Works |
| edge-tts | ✅ Works |
| pyttsx3 | ✅ Works |
| pyautogui | ✅ Works |
| Pillow | ✅ Works |
| psutil | ✅ Works |
| mss | ✅ Works |
| duckduckgo-search | ✅ Works |
| **PyAudio** | ❌ Broken on 3.14 — NOT installed |
| **pygame** | ❌ Broken on 3.14 — NOT installed |
| **playsound** | ❌ Broken on 3.14 — NOT installed |
