@echo off
echo ========================================
echo  Compiling Clawd Pager (no flash)
echo ========================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Run setup.bat first!
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: Compile only - useful for testing config without device
esphome compile clawd-pager.yaml

pause
