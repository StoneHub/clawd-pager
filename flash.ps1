# Flash script for Clawd Pager (runs ESPHome via WSL)
Write-Host "========================================"
Write-Host " Flashing Clawd Pager to M5StickC Plus"
Write-Host "========================================`n"

# Check if device is attached to WSL
$attached = usbipd list 2>$null | Select-String "Attached"
if (-not $attached) {
    Write-Host "NOTE: No USB devices attached to WSL yet.`n" -ForegroundColor Yellow
    Write-Host "Run these commands first (as Admin):"
    Write-Host "  1. usbipd list              # Find your device (look for CP210x or CH340)"
    Write-Host "  2. usbipd bind --busid X-X  # Bind the device (one-time)"
    Write-Host "  3. usbipd attach --wsl --busid X-X  # Attach to WSL`n"
}

# Run ESPHome in WSL
$yamlPath = "/mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml"
wsl bash -c "source ~/esphome-venv/bin/activate && esphome run $yamlPath"
