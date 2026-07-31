#Requires -Version 5.1
# Start WorkSupportPortal on Windows without Docker (waitress).
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File src\scripts\windows\Start-ProductionApp.ps1
# Note: Keep this file ASCII-only. Windows PowerShell 5.1 may fail to parse UTF-8 Japanese.
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message"
}

function Import-EnvFile([string]$Path) {
    $content = Get-Content -LiteralPath $Path -Encoding UTF8
    foreach ($rawLine in $content) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line -notmatch "=") { continue }
        $name, $value = $line -split "=", 2
        $name = $name.Trim().Trim([char]0xFEFF)
        $value = $value.Trim().Trim('"').Trim("'")
        Set-Item -Path "env:$name" -Value $value
    }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Src = Join-Path $Root "src"
if (-not (Test-Path (Join-Path $Src "manage.py"))) {
    throw "Missing src\manage.py under $Root"
}
Set-Location $Src
$env:PYTHONPATH = $Src
if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = "config.settings.production"
}
Write-Step "Project: $Root (cwd: $Src)"

$EnvFile = Join-Path $Root ".env.production"
if (-not (Test-Path $EnvFile)) {
    $txtFile = Join-Path $Root ".env.production.txt"
    if (Test-Path $txtFile) {
        throw 'Missing .env.production. Found .env.production.txt - rename it to .env.production (remove .txt).'
    }
    throw 'Missing .env.production. Run: copy .env.production.example .env.production'
}

Write-Step "Loading .env.production"
Import-EnvFile $EnvFile

if (-not $env:DATABASE_URL -and -not $env:POSTGRES_DB) {
    throw 'Set DATABASE_URL or POSTGRES_DB (and related POSTGRES_*) in .env.production'
}
if ($env:AUTH_DEV_MODE -eq "true") {
    throw 'AUTH_DEV_MODE=true is not allowed in production. Set AUTH_DEV_MODE=false in .env.production'
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw 'Missing .venv. Run: python -m venv .venv then pip install -r requirements-windows-prod.txt'
}

Write-Step "Checking database configuration"
& $Python manage.py check_production_env
if ($LASTEXITCODE -ne 0) {
    throw 'check_production_env failed. See messages above.'
}

Write-Step "Running migrate"
& $Python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    throw 'migrate failed. Check PostgreSQL service and DATABASE_URL / POSTGRES_*.'
}

Write-Step "Running collectstatic"
& $Python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) {
    throw 'collectstatic failed.'
}

Write-Step "Checking waitress"
& $Python -c "import waitress"
if ($LASTEXITCODE -ne 0) {
    throw 'waitress is not installed. Run: .venv\Scripts\pip install -r requirements-windows-prod.txt'
}

$Port = if ($env:APP_PUBLISH_PORT) { $env:APP_PUBLISH_PORT } else { "3000" }
$Listen = "0.0.0.0:${Port}"
Write-Step "Starting waitress on ${Listen} (do not close this window)"
& $Python -m waitress --listen=$Listen config.wsgi:application
