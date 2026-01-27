# Flash script for Clawd Pager (runs ESPHome via WSL)
Write-Host "========================================"
Write-Host " Flashing Clawd Pager to M5StickC Plus"
Write-Host "========================================`n"

# Auto-attach M5Stack USB to WSL
Write-Host "Checking USB device status..." -ForegroundColor Cyan
$usbList = usbipd list 2>$null

# Find M5Stack device line
$m5Line = $usbList | Select-String -Pattern "M5stack|CP210|CH340|0403:6001"
if ($m5Line) {
    # Extract BUSID (first column, format like "2-1")
    $busid = ($m5Line -split '\s+')[0]
    
    # Check if already attached
    if ($m5Line -match "Attached") {
        Write-Host "USB already attached to WSL (BUSID: $busid)" -ForegroundColor Green
    }
    else {
        Write-Host "Attaching USB device (BUSID: $busid) to WSL..." -ForegroundColor Yellow
        usbipd attach --wsl --busid $busid 2>$null
        Start-Sleep -Seconds 2
        Write-Host "USB attached!" -ForegroundColor Green
    }
}
else {
    Write-Host "WARNING: M5Stack device not found!" -ForegroundColor Red
    Write-Host "Make sure the device is plugged in and try again.`n"
    Write-Host "Run 'usbipd list' to see available devices."
    exit 1
}

# Run ESPHome in WSL
$yamlPath = "/mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml"
wsl bash -c "source ~/esphome-venv/bin/activate && esphome run $yamlPath"
