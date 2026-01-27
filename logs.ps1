# View logs from the device
# Usage: .\logs.ps1 [wifi|usb]

param (
    [string]$Mode = "usb"
)

Write-Host "Starting logs in $Mode mode via WSL..." -ForegroundColor Cyan

$yamlPath = "/mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml"
$cmd = "source ~/esphome-venv/bin/activate && esphome logs $yamlPath"

if ($Mode -eq "usb") {
    $cmd = "$cmd --device /dev/ttyUSB1"
}

wsl bash -c "$cmd"
