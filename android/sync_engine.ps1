param(
    [string]$Model = $env:TENSEI_MODEL
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "source\tensei"
$dst = Join-Path $PSScriptRoot "app\src\main\python\tensei"
$assets = Join-Path $PSScriptRoot "app\src\main\assets"

if (-not $Model) {
    $candidates = @(
        (Join-Path $root "TenSeiAi.tsei"),
        (Join-Path $root "model\TenSeiAi.tsei"),
        (Join-Path $assets "TenSeiAi.tsei"),
        (Join-Path $HOME "Downloads\TenSeiAi.tsei")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $Model = $candidate
            break
        }
    }
}

if (Test-Path $dst) {
    Remove-Item -Recurse -Force $dst
}
New-Item -ItemType Directory -Force -Path $dst, $assets | Out-Null
Copy-Item -Recurse -Force (Join-Path $src "*") $dst
Get-ChildItem -Path $dst -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $dst -Recurse -File -Filter "*.pyc" | Remove-Item -Force

Write-Host "engine -> $dst"
if ($Model -and (Test-Path $Model)) {
    Copy-Item -Force $Model (Join-Path $assets "TenSeiAi.tsei")
    Write-Host "model  -> $assets\TenSeiAi.tsei"
} else {
    Write-Host "model not found; place TenSeiAi.tsei in android/app/src/main/assets/"
    Write-Host "or run: .\android\sync_engine.ps1 -Model C:\path\to\TenSeiAi.tsei"
}
