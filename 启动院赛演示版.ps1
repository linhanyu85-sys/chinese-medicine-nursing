param(
  [string]$ApiKey = "",
  [int]$Port = 8791,
  [switch]$Clear
)

$script = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "run_demo.ps1"
$args = @("-ExecutionPolicy", "Bypass", "-File", $script, "-Port", "$Port")
if ($ApiKey) {
  $args += @("-ApiKey", $ApiKey)
}
if ($Clear) {
  $args += "-Clear"
}

& powershell @args
