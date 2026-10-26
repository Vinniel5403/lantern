param(
    [ValidateSet("lcd_test", "lcd_state_test", "esp32dev", "relay_test")]
    [string]$Environment = "lcd_test",

    [string]$Port,

    [ValidateRange(1200, 2000000)]
    [int]$Baud = 115200,

    [switch]$MonitorOnly,
    [switch]$UploadOnly
)

$ErrorActionPreference = "Stop"
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectDirectory

$platformio = Join-Path $env:USERPROFILE ".platformio\penv\Scripts\platformio.exe"
if (-not (Test-Path -LiteralPath $platformio)) {
    throw "ไม่พบ PlatformIO CLI: $platformio"
}

$env:PLATFORMIO_CORE_DIR = Join-Path (Split-Path -Parent $projectDirectory) ".pio-core"

function Invoke-PlatformIO {
    param([string[]]$Arguments)

    & $platformio @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PlatformIO ล้มเหลวด้วย exit code $LASTEXITCODE"
    }
}

if (-not $MonitorOnly) {
    $uploadArguments = @("run", "-e", $Environment, "-t", "upload")
    if ($Port) {
        $uploadArguments += @("--upload-port", $Port)
    }

    Write-Host "Uploading environment '$Environment'..."
    Invoke-PlatformIO -Arguments $uploadArguments
}

if (-not $UploadOnly) {
    $monitorArguments = @("device", "monitor", "-e", $Environment, "-b", $Baud)
    if ($Port) {
        $monitorArguments += @("--port", $Port)
    }

    Write-Host "Opening Serial Monitor at $Baud baud. Press Ctrl+C to exit."
    Invoke-PlatformIO -Arguments $monitorArguments
}
