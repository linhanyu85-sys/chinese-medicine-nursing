param(
  [switch]$Clean
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Join-Path $projectRoot "app-mobile"
$runtimeConfigPath = Join-Path $appRoot "src\generated\runtimeConfig.ts"

if (-not (Test-Path -LiteralPath $appRoot)) {
  throw "app-mobile folder not found: $appRoot"
}

Set-Location -LiteralPath $appRoot

$backendUrlForApk = $env:APP_BACKEND_URL
if ([string]::IsNullOrWhiteSpace($backendUrlForApk)) {
  $backendUrlForApk = "http://47.84.99.189:18791"
}

$runtimeContent = @"
export const runtimeConfig = {
  backendUrl: "$backendUrlForApk",
};
"@
Set-Content -LiteralPath $runtimeConfigPath -Value $runtimeContent -Encoding UTF8
Write-Host "Runtime backend URL for APK: $backendUrlForApk"

if ($Clean) {
  Remove-Item -Recurse -Force ".expo" -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force ".expo-out-temp" -ErrorAction SilentlyContinue
}

function Resolve-NodeDir {
  $candidates = @(
    "C:\Users\58258\AppData\Local\ms-playwright-go\1.50.1",
    "C:\Program Files\nodejs"
  )

  foreach ($dir in $candidates) {
    if (Test-Path -LiteralPath (Join-Path $dir "node.exe")) {
      return $dir
    }
  }

  throw "Node.js not found."
}

function Resolve-EasCmd {
  $candidates = @(
    "C:\Users\58258\AppData\Roaming\npm\eas.cmd",
    "C:\Program Files\nodejs\eas.cmd"
  )

  foreach ($cmd in $candidates) {
    if (Test-Path -LiteralPath $cmd) {
      return $cmd
    }
  }

  throw "eas-cli not found. Run: npm i -g eas-cli"
}

$nodeDir = Resolve-NodeDir
$easCmd = Resolve-EasCmd
$easBinDir = Split-Path -Parent $easCmd
$env:PATH = "$nodeDir;$easBinDir;$env:PATH"
$env:NODE_NO_WARNINGS = "1"

Write-Host "Step 1/4: Check EAS CLI..."
& $easCmd --version
if ($LASTEXITCODE -ne 0) {
  throw "EAS CLI check failed."
}

Write-Host "Step 2/4: Check Expo login..."
$null = & $easCmd whoami 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Not logged in. Starting login..."
  & $easCmd login
  if ($LASTEXITCODE -ne 0) {
    throw "Expo login failed."
  }
}

Write-Host "Step 3/4: Prepare git repo..."
if (-not (Test-Path -LiteralPath ".git")) {
  git init | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "git init failed."
  }
}

Write-Host "Step 4/4: Build Android APK..."
& $easCmd build --platform android --profile preview
if ($LASTEXITCODE -ne 0) {
  throw "APK build failed. See logs above."
}
