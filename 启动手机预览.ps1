param(
  [switch]$Clear,
  [switch]$Tunnel
)

$script = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "run_mobile_preview.ps1"
$args = @("-ExecutionPolicy", "Bypass", "-File", $script)
if ($Clear) {
  $args += "-Clear"
}
if ($Tunnel) {
  $args += "-Tunnel"
}

& powershell @args
