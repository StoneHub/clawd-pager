@echo off
echo ========================================
echo  Viewing Clawd Pager Logs
echo ========================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Run setup.bat first!
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: View logs from the device (useful for debugging)
esphome logs clawd-pager.yaml

pause
