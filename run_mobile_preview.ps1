param(
  [switch]$Clear,
  [switch]$Tunnel,
  [switch]$SkipBackend,
  [string]$HostIp = "",
  [int]$ExpoPort = 0
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Join-Path $projectRoot "app-mobile"
$backendConfigPath = Join-Path $projectRoot "backend\local_config.json"
$runtimeConfigPath = Join-Path $appRoot "src\generated\runtimeConfig.ts"
$preferredExpoPort = 8081

function Resolve-NodeExe {
  $candidates = @(
    "C:\Users\58258\AppData\Local\ms-playwright-go\1.50.1\node.exe",
    "C:\Program Files\nodejs\node.exe"
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  try {
    $cmd = Get-Command node -ErrorAction Stop
    if ($cmd -and $cmd.Source) {
      return $cmd.Source
    }
  } catch {
  }

  throw "Node.js executable not found. Please install Node.js first."
}

function Get-PrimaryIPv4 {
  $candidates = @()
  try {
    $wifi = Get-NetIPConfiguration |
      Where-Object { $_.InterfaceAlias -eq "WLAN" -and $_.IPv4Address } |
      Select-Object -ExpandProperty IPv4Address
    foreach ($item in $wifi) {
      if ($item -and $item.IPAddress) {
        $candidates += [string]$item.IPAddress
      }
    }
  } catch {
  }

  try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254*" -and
        $_.InterfaceAlias -notlike "vEthernet*"
      }
    foreach ($item in $ips) {
      if ($item -and $item.IPAddress) {
        $candidates += [string]$item.IPAddress
      }
    }
  } catch {
  }

  $candidates = $candidates | Select-Object -Unique
  $ten = $candidates | Where-Object { $_ -like "10.*" } | Select-Object -First 1
  if ($ten) { return $ten }

  $oneNineTwo = $candidates | Where-Object { $_ -like "192.168.*" } | Select-Object -First 1
  if ($oneNineTwo) { return $oneNineTwo }

  $oneSevenTwo = $candidates | Where-Object { $_ -like "172.*" } | Select-Object -First 1
  if ($oneSevenTwo) { return $oneSevenTwo }

  if ($candidates.Count -gt 0) {
    return [string]$candidates[0]
  }

  return "127.0.0.1"
}

function Get-FreeTcpPort {
  param(
    [int]$StartPort = 8081,
    [int]$EndPort = 8120
  )

  for ($port = $StartPort; $port -le $EndPort; $port++) {
    $inUse = netstat -ano | Select-String -Pattern (":$port\s")
    if (-not $inUse) {
      return $port
    }
  }

  return $StartPort
}

$nodeExe = Resolve-NodeExe
if (-not (Test-Path (Join-Path $appRoot "node_modules\expo\bin\cli"))) {
  throw "Dependencies are missing in app-mobile. Run npm install in app-mobile first."
}

if (-not $SkipBackend) {
  $backendScript = Join-Path $projectRoot "backend\start_backend.ps1"
  if (Test-Path $backendScript) {
    $backendArgs = @(
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      $backendScript
    )
    Start-Process powershell -ArgumentList $backendArgs | Out-Null
    Start-Sleep -Seconds 2
  }
}

$backendPort = 8790
if (Test-Path $backendConfigPath) {
  try {
    $backendConfig = Get-Content -LiteralPath $backendConfigPath -Raw | ConvertFrom-Json
    if ($backendConfig.port) {
      $backendPort = [int]$backendConfig.port
    }
  } catch {
  }
}

$localIp = if ($HostIp) { $HostIp } else { Get-PrimaryIPv4 }
$expoPort = if ($ExpoPort -gt 0) { $ExpoPort } else { Get-FreeTcpPort -StartPort $preferredExpoPort }
$runtimeContent = @"
export const runtimeConfig = {
  backendUrl: "http://${localIp}:${backendPort}",
};
"@
Set-Content -LiteralPath $runtimeConfigPath -Value $runtimeContent -Encoding UTF8

Set-Location -LiteralPath $appRoot
$hostMode = if ($Tunnel) { "--tunnel" } else { "--lan" }
$env:REACT_NATIVE_PACKAGER_HOSTNAME = $localIp
$args = @(".\node_modules\expo\bin\cli", "start", $hostMode, "--port", "$expoPort")
if ($Clear) {
  $args += "--clear"
}

Write-Host "Backend URL: http://${localIp}:${backendPort}"
Write-Host "Expo Port: $expoPort"
Write-Host "Expo Mode: $hostMode"

& $nodeExe @args
