# Attach M5StickC USB to WSL
# Run this as Administrator!

Write-Host "========================================"
Write-Host " Attach USB Device to WSL"
Write-Host "========================================`n"

# List devices
Write-Host "Available USB devices:`n"
usbipd list

Write-Host "`nLook for your M5StickC (usually shows as CP210x or CH340)`n"
$busid = Read-Host "Enter the BUSID (e.g., 1-3)"

if ($busid) {
    Write-Host "`nBinding device..."
    usbipd bind --busid $busid 2>$null

    Write-Host "Attaching to WSL..."
    usbipd attach --wsl --busid $busid

    Write-Host "`nDone! Device should now be available in WSL." -ForegroundColor Green
    Write-Host "You can verify with: wsl ls /dev/ttyUSB*"
}
