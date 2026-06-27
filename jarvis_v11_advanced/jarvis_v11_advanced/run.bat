@echo off
cd /d "%~dp0"
echo ==========================================
echo   JARVIS OMEGA V11
echo   Python 3.14.5 Compatible
echo ==========================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.14.5 and add it to PATH
    pause
    exit /b 1
)

python --version
echo.

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

if not exist "venv\Lib\site-packages\PyQt6" (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo Starting JARVIS V11...
python main.py
pause
