@echo off
echo ========================================
echo  ESPHome Setup for Clawd Pager
echo ========================================
echo.

:: Look for Python 3.12 or 3.11 (ESPHome doesn't support 3.14 yet)
set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312-arm64\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312-arm64\python.exe"
    echo Found Python 3.12 ARM64
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    echo Found Python 3.12
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311-arm64\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python311-arm64\python.exe"
    echo Found Python 3.11 ARM64
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    echo Found Python 3.11
) else if exist "C:\Python312\python.exe" (
    set "PY=C:\Python312\python.exe"
    echo Found Python 3.12
) else if exist "C:\Python311\python.exe" (
    set "PY=C:\Python311\python.exe"
    echo Found Python 3.11
) else (
    echo ERROR: Python 3.11 or 3.12 not found.
    echo.
    echo ESPHome does not support Python 3.14 yet.
    echo Please install Python 3.12 from:
    echo   https://www.python.org/downloads/release/python-3129/
    echo.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
if exist "venv" (
    echo       Removing old venv with incompatible Python...
    rmdir /s /q venv
)
"%PY%" -m venv venv
echo       Virtual environment created.

echo.
echo [2/3] Activating and installing ESPHome...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install esphome

echo.
echo [3/3] Verifying installation...
esphome version

echo.
echo ========================================
echo  Setup complete!
echo ========================================
echo.
echo Next steps:
echo   1. Plug in your M5StickC Plus via USB
echo   2. Run: flash.bat
echo.
pause
