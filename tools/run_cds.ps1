<#
run_cds.ps1 -- headless CODESYS launcher (simple, reliable).

Facts established by experiment:
  * arguments must be ONE string with quoted paths, otherwise CODESYS cuts the
    script path at the first space and the script never runs;
  * the FIRST launch right after a previous CODESYS exit silently dies
    (exit code 1, no output, no log). The SECOND launch works. So: never kill
    processes pre-emptively, just retry every ~10 s until the log appears.

ASCII-only on purpose (Windows PowerShell reads .ps1 as ANSI).
#>
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$LogName,
    [int]$WaitSec = 900,
    [int]$Tries = 8
)

$ErrorActionPreference = "Continue"
$Root    = Split-Path -Parent $PSScriptRoot
$Exe     = "C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Common\CODESYS.exe"
$WorkDir = "C:\CPM6502_build"
$LogPath = Join-Path $Root "log\$LogName"
$Base    = $Script -replace '\.py$', ''
$OutF    = Join-Path $WorkDir "${Base}_out.txt"
$ErrF    = Join-Path $WorkDir "${Base}_err.txt"

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$argline = '--profile="CODESYS V3.5 SP17 Patch 3" --noUI --runscript="' + (Join-Path $Root "tools\$Script") + '"'

for ($try = 1; $try -le $Tries; $try++) {
    Remove-Item $LogPath -Force -ErrorAction SilentlyContinue
    Remove-Item $OutF, $ErrF -Force -ErrorAction SilentlyContinue

    $p = Start-Process -FilePath $Exe -ArgumentList $argline -WorkingDirectory $WorkDir `
         -RedirectStandardOutput $OutF -RedirectStandardError $ErrF -PassThru

    $started = $false
    $until = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $until) {
        if (Test-Path $LogPath) { $started = $true; break }
        if ($p.HasExited) { break }
        Start-Sleep -Seconds 2
    }

    if (-not $started) {
        Write-Output ("попытка {0}: не стартовал (exit={1})" -f $try, $(if ($p.HasExited) { $p.ExitCode } else { '-' }))
        Start-Sleep -Seconds 12
        continue
    }

    Write-Output ("попытка {0}: скрипт пошёл" -f $try)
    $until = (Get-Date).AddSeconds($WaitSec)
    $gone = $false
    while ((Get-Date) -lt $until) {
        if ($p.HasExited) { $gone = $true; break }
        if (@(Get-Process CODESYS -ErrorAction SilentlyContinue).Count -eq 0) { $gone = $true; break }
        Start-Sleep -Seconds 2
    }
    if ($gone) { Write-Output "OK: finished"; exit 0 }

    Write-Output ("HUNG: killing after {0} s" -f $WaitSec)
    foreach ($x in @(Get-Process CODESYS -ErrorAction SilentlyContinue)) {
        try { Stop-Process -Id $x.Id -Force -ErrorAction Stop; Write-Output ("killed " + $x.Id) } catch { }
    }
    exit 4
}

Write-Output "DID NOT START (все попытки)"
exit 3
