param(
  [string]$ApiKey = "",
  [int]$Port = 18791,
  [string]$AppHost = "0.0.0.0",
  [string]$Model = "kimi-k2.5"
)

$pythonCandidates = @(
  "C:\Users\58258\AppData\Local\Python\bin\python.exe",
  "python"
)

$python = $pythonCandidates | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1
if (-not $python) {
  throw "Python runtime not found."
}

& $python -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('docx') else 1)" | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Installing python-docx..."
  & $python -m pip install python-docx
}

$configPath = Join-Path $PSScriptRoot "local_config.json"
$config = $null
if (Test-Path $configPath) {
  try {
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
  } catch {
    $config = $null
  }
}

if (-not $ApiKey -and $config -and $config.apiKey) {
  $ApiKey = [string]$config.apiKey
}

if ($config -and $config.model -and -not $PSBoundParameters.ContainsKey("Model")) {
  $Model = [string]$config.model
}

if ($config -and $config.port -and -not $PSBoundParameters.ContainsKey("Port")) {
  $Port = [int]$config.port
}

if ($config -and $config.host -and -not $PSBoundParameters.ContainsKey("AppHost")) {
  $AppHost = [string]$config.host
}

if ($ApiKey) {
  $env:ALIYUN_API_KEY = $ApiKey
}

if ($config -and $config.baseUrl) {
  $env:ALIYUN_BASE_URL = [string]$config.baseUrl
}

$env:APP_PORT = "$Port"
$env:APP_HOST = $AppHost
$env:ALIYUN_MODEL = $Model

Set-Location -LiteralPath $PSScriptRoot

try {
  $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($existing -and $existing.OwningProcess) {
    Stop-Process -Id $existing.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
  }
} catch {
}

& $python ".\server.py"
