param(
  [string]$ApiKey = "",
  [int]$Port = 8791,
  [string]$AppHost = "0.0.0.0",
  [string]$Model = "qwen3.5-plus"
)

$script = Join-Path $PSScriptRoot "run_backend.ps1"
$args = @(
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $script,
  "-Port",
  "$Port",
  "-AppHost",
  "$AppHost",
  "-Model",
  "$Model"
)

if ($ApiKey) {
  $args += @("-ApiKey", $ApiKey)
}

& powershell @args
