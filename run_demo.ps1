param(
  [string]$ApiKey = "",
  [int]$Port = 8791,
  [string]$AppHost = "0.0.0.0",
  [switch]$Clear,
  [string]$HostIp = "",
  [int]$ExpoPort = 0,
  [switch]$Tunnel
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendScript = Join-Path $projectRoot "backend\run_backend.ps1"
$appScript = Join-Path $projectRoot "run_mobile_preview.ps1"

$backendArgs = @(
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $backendScript,
  "-Port",
  "$Port",
  "-AppHost",
  "$AppHost"
)

if ($ApiKey) {
  $backendArgs += @("-ApiKey", $ApiKey)
}

Start-Process powershell -ArgumentList $backendArgs | Out-Null
Start-Sleep -Seconds 2

$appArgs = @("-ExecutionPolicy", "Bypass", "-File", $appScript, "-SkipBackend")
if ($Clear) {
  $appArgs += "-Clear"
}
if ($HostIp) {
  $appArgs += @("-HostIp", $HostIp)
}
if ($ExpoPort -gt 0) {
  $appArgs += @("-ExpoPort", "$ExpoPort")
}
if ($Tunnel) {
  $appArgs += "-Tunnel"
}

& powershell @appArgs
