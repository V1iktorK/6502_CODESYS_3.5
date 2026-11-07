<#
run_quick.ps1 -- fast headless launcher for BISECTION probes.

WHY: CODESYS in --noUI can block on an invisible modal dialog. The regular
launcher waits up to 15 minutes for the process to disappear, which makes a
bisection with hangs cost hours. Here the wait after script start is short and
bounded: if the process is still alive after -WaitSec we kill OUR OWN process
and report HUNG. Bisection treats that as "this trial fails" and continues.

NOTE: ASCII-only on purpose (Windows PowerShell reads .ps1 as ANSI).

USAGE:
  powershell -ExecutionPolicy Bypass -File tools\run_quick.ps1 -Script probe_bisect3.py -LogName probe_bisect3.log -WaitSec 75
#>
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$LogName,
    [int]$WaitSec = 75
)

$ErrorActionPreference = "Continue"
$Root    = Split-Path -Parent $PSScriptRoot
$Exe     = "C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Common\CODESYS.exe"
$WorkDir = "C:\CPM6502_build"
$LogPath = Join-Path $Root "log\$LogName"
$Base    = $Script -replace '\.py$', ''

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

function Get-Cds { @(Get-Process CODESYS -ErrorAction SilentlyContinue) }

# 1) wait for a free instance (max 150 s)
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Cds).Count -ne 0 -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds (Get-Random -Minimum 3 -Maximum 8)
}
if ((Get-Cds).Count -ne 0) {
    foreach ($x in (Get-Cds)) { try { Stop-Process -Id $x.Id -Force -ErrorAction Stop } catch { } }
    Start-Sleep -Seconds 4
}

Remove-Item $LogPath -Force -ErrorAction SilentlyContinue

$p = Start-Process -FilePath $Exe -WorkingDirectory $WorkDir `
     -ArgumentList @('--profile="CODESYS V3.5 SP17 Patch 3"', '--noUI',
                     "--runscript=`"$Root\tools\$Script`"") `
     -RedirectStandardOutput (Join-Path $Root "log\${Base}_out.txt") `
     -RedirectStandardError  (Join-Path $Root "log\${Base}_err.txt") `
     -NoNewWindow -PassThru

# 2) wait for the log file (the script writes it as its first action)
$started = $false
$until = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $until) {
    if (Test-Path $LogPath) { $started = $true; break }
    if ($p.HasExited) { break }
    Start-Sleep -Seconds 1
}

if (-not $started) {
    Write-Output "DID NOT START"
    foreach ($x in (Get-Cds)) { try { Stop-Process -Id $x.Id -Force -ErrorAction Stop } catch { } }
    exit 3
}

# 3) bounded wait for finish
$until = (Get-Date).AddSeconds($WaitSec)
$gone = $false
while ((Get-Date) -lt $until) {
    if ((Get-Cds).Count -eq 0) { $gone = $true; break }
    Start-Sleep -Seconds 1
}

if ($gone) {
    Write-Output "OK: finished within $WaitSec s"
    exit 0
}

Write-Output "HUNG: killing own process after $WaitSec s"
foreach ($x in (Get-Cds)) {
    try { Stop-Process -Id $x.Id -Force -ErrorAction Stop; Write-Output ("killed " + $x.Id) } catch { }
}
Start-Sleep -Seconds 3
exit 4
