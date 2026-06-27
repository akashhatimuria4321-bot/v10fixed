@echo off
title JARVIS OMEGA V10 — INSTALLER
color 0B
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║         JARVIS OMEGA V10 — Python 3.14 Installer        ║
echo  ║         100%% FREE  -  No API Keys Required              ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Check Python ──────────────────────────────────────────────────────────
python --version 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH. Install Python 3.14 first.
    pause & exit /b 1
)

:: ── Upgrade pip silently ──────────────────────────────────────────────────
echo [1/6] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: ── Core deps ─────────────────────────────────────────────────────────────
echo [2/6] Installing core packages (PyQt6, requests, sounddevice)...
pip install PyQt6 requests sounddevice numpy --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Core install failed. Check internet connection.
    pause & exit /b 1
)

:: ── TTS ───────────────────────────────────────────────────────────────────
echo [3/6] Installing TTS (edge-tts, pyttsx3)...
pip install edge-tts pyttsx3 --quiet
:: Do NOT install pygame or playsound — broken on Python 3.14

:: ── STT ───────────────────────────────────────────────────────────────────
echo [4/6] Installing STT (SpeechRecognition)...
pip install SpeechRecognition --quiet
:: Do NOT install PyAudio — broken on Python 3.14, sounddevice replaces it

:: ── Computer Control + OCR ────────────────────────────────────────────────
echo [5/6] Installing PC control + OCR (pyautogui, Pillow, psutil, mss)...
pip install pyautogui pygetwindow psutil keyboard Pillow pytesseract mss --quiet

:: ── Web Search ────────────────────────────────────────────────────────────
echo [6/6] Installing web search (duckduckgo-search)...
pip install duckduckgo-search --quiet

:: ── Data directories ──────────────────────────────────────────────────────
if not exist "data\screenshots" mkdir "data\screenshots"
if not exist "data" mkdir "data"
if not exist "config" mkdir "config"

:: ── Tesseract notice ──────────────────────────────────────────────────────
echo.
echo  ┌─────────────────────────────────────────────────────────┐
echo  │ OPTIONAL: Tesseract OCR (for screen reading)            │
echo  │ Download: https://github.com/UB-Mannheim/tesseract/wiki │
echo  │ After install, add to PATH or it works without it too.  │
echo  └─────────────────────────────────────────────────────────┘

:: ── Ollama check ──────────────────────────────────────────────────────────
echo.
echo  Checking Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Ollama not found.
    echo  [!] Download from: https://ollama.com/download
    echo  [!] After install, run in a terminal: ollama serve
) else (
    echo  [OK] Ollama is installed!
    echo  [OK] Your models are already pulled ^(llama3.2, qwen3-vl, etc^)
)

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  Installation complete!                                  ║
echo  ║                                                          ║
echo  ║  TO START JARVIS:                                        ║
echo  ║    Step 1: Open a terminal → type: ollama serve          ║
echo  ║    Step 2: Double-click run.bat  (or: python main.py)    ║
echo  ║                                                          ║
echo  ║  SHORTCUTS:                                              ║
echo  ║    SPACE      = Toggle microphone / voice input          ║
echo  ║    Ctrl+J     = Show chat panel                          ║
echo  ║    Ctrl+O     = Show output panel                        ║
echo  ║    Ctrl+S     = Quick screenshot                         ║
echo  ║    Ctrl+T     = Settings                                 ║
echo  ║    ESC        = Minimize to floating J ball              ║
echo  ║    Ctrl+Q     = Quit                                     ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
