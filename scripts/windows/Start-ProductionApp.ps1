#Requires -Version 5.1
# Start WorkSupportPortal on Windows without Docker (waitress).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\windows\Start-ProductionApp.ps1
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
Set-Location $Root
Write-Step "プロジェクト: $Root"

$EnvFile = Join-Path $Root ".env.production"
if (-not (Test-Path $EnvFile)) {
    $txtFile = Join-Path $Root ".env.production.txt"
    if (Test-Path $txtFile) {
        throw ".env.production がありません。`.env.production.txt` があります。拡張子 .txt を外して `.env.production` にリネームしてください。"
    }
    throw ".env.production が見つかりません。copy .env.production.example .env.production して編集してください。"
}

Write-Step ".env.production を読み込み"
Import-EnvFile $EnvFile

if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL が未設定です。.env.production に postgresql://... を設定してください。"
}
if ($env:AUTH_DEV_MODE -eq "true") {
    throw "本番では AUTH_DEV_MODE=true は禁止です。.env.production を false にしてください。"
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw ".venv がありません。python -m venv .venv のあと pip install -r requirements-windows-prod.txt を実行してください。"
}

Write-Step "DB 接続確認"
& $Python manage.py check_production_env
if ($LASTEXITCODE -ne 0) {
    throw "check_production_env が失敗しました。上の表示を確認してください。"
}

Write-Step "migrate"
& $Python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    throw "migrate が失敗しました。PostgreSQL の起動と DATABASE_URL を確認してください。"
}

Write-Step "collectstatic"
& $Python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) {
    throw "collectstatic が失敗しました。"
}

Write-Step "waitress の確認"
& $Python -c "import waitress"
if ($LASTEXITCODE -ne 0) {
    throw "waitress が未インストールです。.venv\Scripts\pip install -r requirements-windows-prod.txt を実行してください。"
}

$Port = if ($env:APP_PUBLISH_PORT) { $env:APP_PUBLISH_PORT } else { "3000" }
$Listen = "0.0.0.0:${Port}"
Write-Step "Starting waitress on ${Listen} (このウィンドウを閉じると停止します)"
& $Python -m waitress --listen=$Listen config.wsgi:application
