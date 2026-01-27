# Compile script for Clawd Pager (runs ESPHome via WSL)
Write-Host "========================================"
Write-Host " Compiling Clawd Pager (no flash)"
Write-Host "========================================`n"

$yamlPath = "/mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml"
wsl bash -c "source ~/esphome-venv/bin/activate && esphome compile $yamlPath"
