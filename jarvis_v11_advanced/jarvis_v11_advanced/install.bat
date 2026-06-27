@echo off
cd /d "%~dp0"
echo ==========================================
echo   JARVIS OMEGA V11 - Installer
echo ==========================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please download Python 3.14.5 from https://python.org
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo Installing packages for Python 3.14.5...
echo This may take a few minutes...
echo.

pip install --upgrade pip

pip install PyQt6>=6.4.0
pip install requests>=2.28.0
pip install SpeechRecognition>=3.10.0
pip install sounddevice>=0.4.6
pip install numpy>=1.24.0
pip install edge-tts>=6.1.9
pip install pyttsx3>=2.90
pip install pyautogui>=0.9.54
pip install pygetwindow>=0.0.9
pip install psutil>=5.9.0
pip install keyboard>=0.13.5
pip install Pillow>=9.5.0
pip install pytesseract>=0.3.10
pip install mss>=9.0.0
pip install duckduckgo-search>=3.9.0
pip install colorama>=0.4.6

echo.
echo ==========================================
echo   Installation Complete!
echo ==========================================
echo.
echo To start JARVIS, run: run.bat
echo.
pause
