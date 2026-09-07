# Groundcheck backend launcher — serve.py (HTTP data API) + ws_proxy.py (live feed).
Set-Location -Path $PSScriptRoot

Write-Host "Groundcheck backend"
Write-Host "===================="
$useBackground = Read-Host "Run in background (detached, keeps running after this window closes)? (y/n)"
$useLogs = Read-Host "Enable logs? (y/n)"

if ($useLogs -match '^[Yy]') {
    $serveOut = Join-Path $PSScriptRoot "serve.log"
    $wsOut = Join-Path $PSScriptRoot "ws_proxy.log"
} else {
    $serveOut = "NUL"
    $wsOut = "NUL"
}

if ($useBackground -match '^[Yy]') {
    Start-Process -FilePath "python" -ArgumentList "serve.py" -WindowStyle Hidden `
        -RedirectStandardOutput $serveOut -RedirectStandardError $serveOut
    Start-Process -FilePath "python" -ArgumentList "ws_proxy.py" -WindowStyle Hidden `
        -RedirectStandardOutput $wsOut -RedirectStandardError $wsOut
    Write-Host "Started in background (detached processes)."
} else {
    Start-Process -FilePath "python" -ArgumentList "serve.py" -NoNewWindow `
        -RedirectStandardOutput $serveOut -RedirectStandardError $serveOut
    Start-Process -FilePath "python" -ArgumentList "ws_proxy.py" -NoNewWindow `
        -RedirectStandardOutput $wsOut -RedirectStandardError $wsOut
    Write-Host "Started in this shell's process tree (close this window to stop)."
}

Start-Sleep -Seconds 1

$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1 -ExpandProperty IPAddress)
if (-not $lanIp) { $lanIp = "unknown" }

Write-Host ""
Write-Host "Groundcheck backend running:"
Write-Host "  Data API:   http://localhost:8765/api/data"
Write-Host "              http://$lanIp:8765/api/data"
Write-Host "  Live feed:  ws://localhost:8766"
Write-Host "              ws://$lanIp:8766"

if ($useLogs -match '^[Yy]') {
    Write-Host ""
    Write-Host "Logs: serve.log, ws_proxy.log"
}
