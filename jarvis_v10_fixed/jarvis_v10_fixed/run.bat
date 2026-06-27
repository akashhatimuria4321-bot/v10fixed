@echo off
title JARVIS OMEGA V10
color 0B

:: Check if Ollama is running
curl -s http://localhost:11434 >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ══════════════════════════════════════════════════════════
    echo   WARNING: Ollama is NOT running!
    echo   Open a NEW terminal window and type:  ollama serve
    echo   Then come back here and press any key.
    echo  ══════════════════════════════════════════════════════════
    echo.
    pause
)

echo  Starting JARVIS OMEGA V10...
echo  (If Ollama is running in another terminal, JARVIS will respond)
echo.
python main.py

if %errorlevel% neq 0 (
    echo.
    echo  JARVIS exited with an error. Check the output above.
    echo  Common fix: pip install PyQt6 requests sounddevice numpy
    pause
)
