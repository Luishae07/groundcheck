# Groundcheck backend launcher — serve.py (HTTP data API) + ws_proxy.py (live feed).
Set-Location -Path $PSScriptRoot

Write-Host "Groundcheck backend"
Write-Host "===================="

# --- check for WSL and a usable Linux distro ---
$wslDistro = $null
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    try {
        $distros = (wsl -l -q 2>$null) | Where-Object { $_ -and $_.Trim() -ne "" }
        if ($distros) { $wslDistro = ($distros | Select-Object -First 1).Trim() }
    } catch { $wslDistro = $null }
}

if ($wslDistro) {
    Write-Host "> Install with WSL"
    Write-Host "  Found WSL distro: $wslDistro"
    $useWsl = Read-Host "Run the backend inside WSL instead (uses start.sh, with cron support)? (y/n)"
    if ($useWsl -match '^[Yy]') {
        $wslPath = (wsl -d $wslDistro wslpath -a "$PSScriptRoot").Trim()
        Write-Host "Handing off to start.sh inside WSL ($wslDistro)..."
        wsl -d $wslDistro bash -c "cd '$wslPath' && chmod +x start.sh && ./start.sh"
        exit
    }
} else {
    Write-Host "> Install WSL"
    Write-Host "  No WSL Linux distro detected. For the full experience (cron-based"
    Write-Host "  scheduling instead of Task Scheduler), install WSL first:"
    Write-Host "    wsl --install"
    Write-Host "  Then re-run this script. Continuing with native Windows/PowerShell for now..."
}

if (-not (Test-Path (Join-Path $PSScriptRoot "data.json"))) {
    $createData = Read-Host "data.json not found. Create it now? (y/n)"
    if ($createData -match '^[Yy]') {
        Start-Sleep -Seconds 2
        Write-Host "How many days of history should the initial fetch cover?"
        Write-Host "  1) 50"
        Write-Host "  2) 200"
        Write-Host "  3) 500"
        Write-Host "  4) 600"
        Write-Host "  5) 800"
        $choice = Read-Host "#?"
        $daysMap = @{ "1" = 50; "2" = 200; "3" = 500; "4" = 600; "5" = 800 }
        $days = $daysMap[$choice]
        if (-not $days) { $days = 50 }
        Write-Host "Fetching last $days day(s) of radiosonde history — this can take a while for large ranges..."
        python update.py --days $days
        Write-Host "data.json created."
    }
}

$useBackground = Read-Host "Run in background (detached, keeps running after this window closes)? (y/n)"
$useLogs = Read-Host "Enable logs? (y/n)"

if ($useLogs -match '^[Yy]') {
    $serveOut = Join-Path $PSScriptRoot "serve.log"
    $wsOut = Join-Path $PSScriptRoot "ws_proxy.log"
} else {
    $serveOut = "NUL"
    $wsOut = "NUL"
}

# --- schedule radiosonde checks: every minute + once daily, via Task Scheduler ---
try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $minAction = New-ScheduledTaskAction -Execute $pythonPath -Argument "update.py --window 60" -WorkingDirectory $PSScriptRoot
    $minTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration ([TimeSpan]::MaxValue)
    Register-ScheduledTask -TaskName "GroundcheckBackendMinuteCheck" -Action $minAction -Trigger $minTrigger -Force -ErrorAction Stop | Out-Null

    $dayAction = New-ScheduledTaskAction -Execute $pythonPath -Argument "update.py --window 86400" -WorkingDirectory $PSScriptRoot
    $dayTrigger = New-ScheduledTaskTrigger -Daily -At "3:00AM"
    Register-ScheduledTask -TaskName "GroundcheckBackendDailyCheck" -Action $dayAction -Trigger $dayTrigger -Force -ErrorAction Stop | Out-Null

    Write-Host "Scheduled radiosonde checks: every minute + once daily (Task Scheduler)."
} catch {
    Write-Host "Could not register scheduled tasks (may need to run as Administrator) — skipping automatic radiosonde checks."
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
