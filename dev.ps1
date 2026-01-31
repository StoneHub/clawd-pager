<#
.SYNOPSIS
    Clawd Pager Development Script - Unified build, upload, and monitoring commands.

.DESCRIPTION
    Provides streamlined development commands for the Clawd Pager project:
    - compile: Validate and compile ESPHome firmware
    - upload: OTA upload to device
    - watch: Compile + Upload + Tail logs
    - logs: Stream device logs
    - dashboard: Open development dashboard
    - session: Start a recording session

.EXAMPLE
    .\dev.ps1 compile
    .\dev.ps1 upload
    .\dev.ps1 watch
    .\dev.ps1 dashboard
    .\dev.ps1 session "Testing button latency"

.NOTES
    Device IP: 192.168.50.85
    ESPHome Version: 2024.12.4 (DO NOT UPGRADE)
#>

param (
    [Parameter(Position = 0)]
    [ValidateSet("compile", "upload", "watch", "logs", "dashboard", "session", "help")]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Notes = ""
)

# === Configuration ===
$DEVICE_IP = "192.168.50.85"
$DEVICE_PORT = 6053
$DASHBOARD_PORT = 8080
$PI_IP = "192.168.50.50"
$YAML_FILE = "clawd-pager.yaml"
$ESPHOME_ENV = "/home/monroe/clawd/esphome-env"

# Colors
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorWarning = "Yellow"
$ColorInfo = "Cyan"
$ColorDim = "DarkGray"

# === Helper Functions ===
function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "=== $Text ===" -ForegroundColor $ColorInfo
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] $Text" -ForegroundColor $ColorDim
}

function Write-Success {
    param([string]$Text)
    Write-Host $Text -ForegroundColor $ColorSuccess
}

function Write-Failure {
    param([string]$Text)
    Write-Host $Text -ForegroundColor $ColorError
}

function Test-DeviceReachable {
    Write-Step "Checking device at $DEVICE_IP..."
    $result = Test-Connection -ComputerName $DEVICE_IP -Count 1 -Quiet -TimeoutSeconds 2
    if ($result) {
        Write-Success "Device reachable"
        return $true
    } else {
        Write-Failure "Device not reachable at $DEVICE_IP"
        return $false
    }
}

function Get-YamlPath {
    # Convert Windows path to WSL path
    $windowsPath = (Get-Location).Path
    $wslPath = $windowsPath -replace '\\', '/' -replace '^([A-Za-z]):', '/mnt/$1'.ToLower()
    return "$wslPath/$YAML_FILE"
}

function Send-DashboardEvent {
    param(
        [string]$EventType,
        [hashtable]$Data
    )

    try {
        $body = @{
            source = "user"
            event_type = $EventType
            data = $Data
        } | ConvertTo-Json

        Invoke-RestMethod -Uri "http://${PI_IP}:${DASHBOARD_PORT}/api/log" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 2 `
            -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Dashboard may not be running, that's OK
    }
}

# === Commands ===
function Start-Compile {
    Write-Header "COMPILING FIRMWARE"

    Write-Host "Config:  $YAML_FILE"
    Write-Host "Target:  M5StickC Plus 1.1"
    Write-Host "ESPHome: 2024.12.4"
    Write-Host ""

    $yamlPath = Get-YamlPath
    $startTime = Get-Date

    Send-DashboardEvent -EventType "BUILD_START" -Data @{ yaml_file = $YAML_FILE }

    Write-Step "Running ESPHome compile..."

    $result = wsl bash -c "source $ESPHOME_ENV/bin/activate && esphome compile $yamlPath 2>&1"
    $exitCode = $LASTEXITCODE

    $duration = ((Get-Date) - $startTime).TotalSeconds

    if ($exitCode -eq 0) {
        Write-Header "BUILD SUCCESS"
        Write-Host "Duration: $([math]::Round($duration, 1))s" -ForegroundColor $ColorSuccess

        # Try to show firmware size
        $buildDir = ".esphome/build/clawd-pager/.pioenvs/clawd-pager"
        if (Test-Path "$buildDir/firmware.bin") {
            $size = (Get-Item "$buildDir/firmware.bin").Length / 1KB
            Write-Host "Firmware: $([math]::Round($size, 1)) KB" -ForegroundColor $ColorDim
        }

        Send-DashboardEvent -EventType "BUILD_END" -Data @{
            success = $true
            duration_s = [math]::Round($duration, 1)
        }

        return $true
    } else {
        Write-Header "BUILD FAILED"
        Write-Host $result -ForegroundColor $ColorError

        Send-DashboardEvent -EventType "BUILD_END" -Data @{
            success = $false
            duration_s = [math]::Round($duration, 1)
        }

        return $false
    }
}

function Start-Upload {
    Write-Header "UPLOADING VIA OTA"

    if (-not (Test-DeviceReachable)) {
        Write-Failure "Cannot upload - device unreachable"
        return $false
    }

    $yamlPath = Get-YamlPath
    $startTime = Get-Date

    Send-DashboardEvent -EventType "OTA_START" -Data @{ target_ip = $DEVICE_IP }

    Write-Step "Starting OTA upload to $DEVICE_IP..."

    wsl bash -c "source $ESPHOME_ENV/bin/activate && esphome upload $yamlPath --device $DEVICE_IP"
    $exitCode = $LASTEXITCODE

    $duration = ((Get-Date) - $startTime).TotalSeconds

    if ($exitCode -eq 0) {
        Write-Success "Upload complete in $([math]::Round($duration, 1))s"

        Send-DashboardEvent -EventType "OTA_END" -Data @{
            success = $true
            duration_s = [math]::Round($duration, 1)
        }

        return $true
    } else {
        Write-Failure "Upload failed after $([math]::Round($duration, 1))s"

        Send-DashboardEvent -EventType "OTA_END" -Data @{
            success = $false
            duration_s = [math]::Round($duration, 1)
        }

        return $false
    }
}

function Start-Watch {
    Write-Header "WATCH MODE"
    Write-Host "Compile -> Upload -> Logs"
    Write-Host ""

    $compiled = Start-Compile
    if (-not $compiled) {
        return
    }

    $uploaded = Start-Upload
    if (-not $uploaded) {
        return
    }

    Write-Header "TAILING LOGS"
    Write-Host "Press Ctrl+C to stop"
    Write-Host ""

    $yamlPath = Get-YamlPath
    wsl bash -c "source $ESPHOME_ENV/bin/activate && esphome logs $yamlPath --device $DEVICE_IP"
}

function Start-Logs {
    Write-Header "DEVICE LOGS"

    if (-not (Test-DeviceReachable)) {
        Write-Failure "Cannot connect - device unreachable"
        return
    }

    Write-Host "Streaming from $DEVICE_IP..."
    Write-Host "Press Ctrl+C to stop"
    Write-Host ""

    $yamlPath = Get-YamlPath
    wsl bash -c "source $ESPHOME_ENV/bin/activate && esphome logs $yamlPath --device $DEVICE_IP"
}

function Open-Dashboard {
    Write-Header "DEVELOPMENT DASHBOARD"

    $url = "http://${PI_IP}:${DASHBOARD_PORT}"

    Write-Host "Opening: $url"
    Write-Host ""
    Write-Host "If the dashboard isn't running, start it on the Pi with:"
    Write-Host "  python -m devtools.dashboard_server" -ForegroundColor $ColorDim
    Write-Host ""

    Start-Process $url
}

function Start-Session {
    param([string]$SessionNotes)

    Write-Header "RECORDING SESSION"

    if ($SessionNotes) {
        Write-Host "Notes: $SessionNotes"
    }
    Write-Host ""

    try {
        $body = @{ notes = $SessionNotes } | ConvertTo-Json

        $response = Invoke-RestMethod -Uri "http://${PI_IP}:${DASHBOARD_PORT}/api/session/start" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 5

        Write-Success "Session started: $($response.session_id)"
        Write-Host ""
        Write-Host "End the session from the dashboard or run:"
        Write-Host "  Invoke-RestMethod -Uri 'http://${PI_IP}:${DASHBOARD_PORT}/api/session/end' -Method POST" -ForegroundColor $ColorDim

    } catch {
        Write-Failure "Failed to start session - is the dashboard running?"
        Write-Host ""
        Write-Host "Start the dashboard on the Pi first:"
        Write-Host "  python -m devtools.dashboard_server" -ForegroundColor $ColorDim
    }
}

function Show-Help {
    Write-Host ""
    Write-Host "Clawd Pager Development Script" -ForegroundColor $ColorInfo
    Write-Host "===============================" -ForegroundColor $ColorInfo
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  compile    Validate and compile ESPHome firmware"
    Write-Host "  upload     OTA upload to device at $DEVICE_IP"
    Write-Host "  watch      Compile + Upload + Tail logs (full cycle)"
    Write-Host "  logs       Stream device logs"
    Write-Host "  dashboard  Open development dashboard in browser"
    Write-Host "  session    Start a recording session with optional notes"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor $ColorDim
    Write-Host "  .\dev.ps1 compile"
    Write-Host "  .\dev.ps1 upload"
    Write-Host "  .\dev.ps1 watch"
    Write-Host "  .\dev.ps1 session 'Testing button B latency'"
    Write-Host ""
    Write-Host "Device: $DEVICE_IP (M5StickC Plus 1.1)"
    Write-Host "ESPHome: 2024.12.4 (DO NOT UPGRADE - HA compatibility)"
    Write-Host ""
}

# === Main ===
switch ($Command) {
    "compile"   { Start-Compile }
    "upload"    { Start-Upload }
    "watch"     { Start-Watch }
    "logs"      { Start-Logs }
    "dashboard" { Open-Dashboard }
    "session"   { Start-Session -SessionNotes $Notes }
    "help"      { Show-Help }
    default     { Show-Help }
}
