# Upload-only script - uses pre-compiled firmware
# Supports both USB and WiFi (OTA) upload
Write-Host "========================================"
Write-Host " Uploading Clawd Pager (skip compile)"
Write-Host "========================================`n"

# Check for WiFi device first
Write-Host "Checking for device on network..." -ForegroundColor Cyan
$pingResult = Test-Connection -ComputerName "clawd-pager.local" -Count 1 -Quiet -TimeoutSeconds 2

if ($pingResult) {
    Write-Host "Device found on WiFi (clawd-pager.local)" -ForegroundColor Green
    $choice = Read-Host "Upload via [W]iFi (OTA) or [U]SB? (default: W)"
    
    if ($choice -eq "U" -or $choice -eq "u") {
        $useWifi = $false
    } else {
        $useWifi = $true
    }
} else {
    Write-Host "Device not found on WiFi, using USB..." -ForegroundColor Yellow
    $useWifi = $false
}

if ($useWifi) {
    Write-Host "`nUploading via WiFi (OTA)..." -ForegroundColor Green
    $yamlPath = "/mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml"
    wsl bash -c "source ~/esphome-venv/bin/activate && esphome upload $yamlPath --device clawd-pager.local"
} else {
    # Auto-attach M5Stack USB to WSL
    Write-Host "`nChecking USB device status..." -ForegroundColor Cyan
    $usbList = usbipd list 2>$null
    $m5Line = $usbList | Select-String -Pattern "M5stack|CP210|CH340|0403:6001"

    if ($m5Line) {
        $busid = ($m5Line -split '\s+')[0]
        if (-not ($m5Line -match "Attached")) {
            Write-Host "Attaching USB (BUSID: $busid)..." -ForegroundColor Yellow
            usbipd attach --wsl --busid $busid 2>$null
            Start-Sleep -Seconds 2
        }
        Write-Host "Uploading via USB..." -ForegroundColor Green
        $yamlPath = "/mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml"
        wsl bash -c "source ~/esphome-venv/bin/activate && esphome upload $yamlPath --device /dev/ttyUSB1"
    } else {
        Write-Host "ERROR: M5Stack not found on USB!" -ForegroundColor Red
        exit 1
    }
}
