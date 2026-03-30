param(
  [string]$ApiKey = "",
  [int]$Port = 18791,
  [string]$AppHost = "0.0.0.0",
  [string]$Model = "kimi-k2.5"
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
