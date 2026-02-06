@echo off
echo ========================================
echo  Flashing Clawd Pager to M5StickC Plus
echo ========================================
echo.

:: Activate virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Run setup.bat first!
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Make sure your M5StickC Plus is plugged in via USB.
echo.

:: Run ESPHome - it will auto-detect the COM port
esphome run clawd-pager.yaml

pause
