<#
run_headless.ps1 -- reliable headless launch of a CODESYS script.

WHY: CODESYS allows only ONE instance per profile. If another session (a parallel
Z80 task runs in this workspace) holds the instance, the launch is silently
swallowed: the process starts, the script never runs, .project stays locked.

ALGORITHM:
  1) wait until no CODESYS process exists for several consecutive checks;
  2) launch the script;
  3) success is detected NOT by exit code (it lies) but by the log file that the
     script writes as its very first action;
  4) if no log appeared -- kill the stuck process and retry.

NOTE: this file is intentionally ASCII-only. Windows PowerShell reads .ps1 as
ANSI unless a BOM is present, so non-ASCII literals here break the parser.

USAGE:
  powershell -ExecutionPolicy Bypass -File tools\run_headless.ps1 -Script probe_fbd.py -LogName probe_fbd.log
#>
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$LogName,
    [int]$TimeoutMin = 30,
    [int]$Runs = 3
)

$ErrorActionPreference = "Continue"
$Root    = Split-Path -Parent $PSScriptRoot
$Exe     = "C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Common\CODESYS.exe"
$WorkDir = "C:\CPM6502_build"
$LogPath = Join-Path $Root "log\$LogName"
$Base    = $Script -replace '\.py$', ''

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

function Get-CdsCount { @(Get-Process CODESYS -ErrorAction SilentlyContinue).Count }

function Kill-OwnStale {
    <# Снимаем ТОЛЬКО свои зависшие процессы (по имени скрипта в командной строке).
       Чужие процессы не трогаем: в рабочей папке параллельно работает другая
       сессия, и убийство её инстанса провоцирует её же на новый запуск --
       получается взаимная блокировка, где страдают оба. #>
    try {
        Get-CimInstance Win32_Process -Filter "Name='CODESYS.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and $_.CommandLine -match [regex]::Escape($Script) } |
            ForEach-Object {
                try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
                      Write-Output ("killed own stale PID=" + $_.ProcessId) } catch { }
            }
    } catch { }
}

function Launch-Once {
    <# Пытаемся запуститься СРАЗУ, как только инстанс свободен.
       Раньше здесь было ожидание "несколько проверок подряд без CODESYS", но
       против симметричного конкурента это дает взаимную блокировку: обе стороны
       ждут тишины и обе не дожидаются. Случайная пауза ломает симметрию. #>
    Remove-Item $LogPath -Force -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath $Exe -WorkingDirectory $WorkDir `
         -ArgumentList @('--profile="CODESYS V3.5 SP17 Patch 3"', '--noUI',
                         "--runscript=`"$Root\tools\$Script`"") `
         -RedirectStandardOutput (Join-Path $Root "log\${Base}_out.txt") `
         -RedirectStandardError  (Join-Path $Root "log\${Base}_err.txt") `
         -NoNewWindow -PassThru

    $waitUntil = (Get-Date).AddSeconds(150).Ticks
    $started = $false
    while ((Get-Date).Ticks -lt $waitUntil) {
        if (Test-Path $LogPath) { $started = $true; break }
        if ($p.HasExited) { break }
        Start-Sleep -Seconds 2
    }
    return $started
}

for ($run = 1; $run -le $Runs; $run++) {
    Write-Output ("=== RUN " + $run + " of " + $Runs + " : " + $Script + " ===")

    # ждем момента, когда инстанс свободен, и бьем СРАЗУ
    $deadline = (Get-Date).AddMinutes($TimeoutMin).Ticks
    while ((Get-CdsCount) -ne 0 -and (Get-Date).Ticks -lt $deadline) {
        Start-Sleep -Seconds (Get-Random -Minimum 3 -Maximum 12)
    }
    if ((Get-CdsCount) -ne 0) {
        Write-Output "TIMEOUT: CODESYS instance is busy (parallel session)"
        exit 2
    }

    $started = Launch-Once

    if ($started) {
        Write-Output "script started; waiting for CODESYS to finish (script calls system.exit())..."
        # Ждем ИСЧЕЗНОВЕНИЯ процесса, а не $p.WaitForExit: Start-Process возвращает
        # объект процесса-лаунчера, который может выйти раньше самого CODESYS.
        # Убивать процесс НЕЛЬЗЯ: в IronPython незаписанный буфер лога теряется.
        $cap = (Get-Date).AddMinutes(15).Ticks
        while ((Get-Date).Ticks -lt $cap) {
            if ((Get-CdsCount) -eq 0) { break }
            Start-Sleep -Seconds 3
        }
        $size = 0
        if (Test-Path $LogPath) { $size = (Get-Item $LogPath).Length }
        Write-Output ("DONE: log " + $LogPath + " (" + $size + " bytes)")
        exit 0
    }

    Write-Output "DID NOT START (instance taken). Cleaning up OWN process and retrying."
    Kill-OwnStale
    Start-Sleep -Seconds (Get-Random -Minimum 5 -Maximum 20)
}

Write-Output ("FAILED to launch after " + $Runs + " attempts")
exit 3
