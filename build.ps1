# ESPHome Build Script for Windows
# Usage: .\build.ps1 [compile|flash-usb|flash-ota|logs]

param(
    [Parameter(Position=0)]
    [ValidateSet('compile','flash-usb','flash-ota','logs')]
    [string]$Action = 'compile',
    
    [string]$ComPort = 'COM3',
    [string]$DeviceIP = '192.168.50.81'
)

$ConfigFile = "clawd-pager-epaper.yaml"

Write-Host "🦞 Clawd Pager ePaper Build Tool" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

switch ($Action) {
    'compile' {
        Write-Host "📦 Compiling firmware..." -ForegroundColor Yellow
        docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome compile $ConfigFile
    }
    
    'flash-usb' {
        Write-Host "🔌 Flashing via USB ($ComPort)..." -ForegroundColor Yellow
        Write-Host "⚠️  Note: If this fails, use ESPHome Web Flasher instead`n" -ForegroundColor Yellow
        docker run --rm -v "${PWD}:/config" --device=$ComPort ghcr.io/esphome/esphome run $ConfigFile --device $ComPort
    }
    
    'flash-ota' {
        Write-Host "📡 Flashing via OTA ($DeviceIP)..." -ForegroundColor Yellow
        docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome run $ConfigFile --device $DeviceIP
    }
    
    'logs' {
        Write-Host "📋 Viewing logs ($DeviceIP)..." -ForegroundColor Yellow
        docker run --rm -v "${PWD}:/config" ghcr.io/esphome/esphome logs $ConfigFile --device $DeviceIP
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Success!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
}
