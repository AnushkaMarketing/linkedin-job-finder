param([switch]$Rebuild)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$signalPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $signalPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required. Install Python and try again.' }
    & $signalPython -m pip install -r requirements.lock
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'node_modules'))) {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Node dependency installation failed. Node 22+ is required.' }
}
if ($Rebuild -or -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'dist\index.html'))) {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Interface build failed. Review the errors above.' }
}
Write-Host 'Signal is starting at http://127.0.0.1:8765'
Write-Host 'Keep this terminal open. Press Ctrl+C to stop.'
& $signalPython -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8765
