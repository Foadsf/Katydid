# SPDX-License-Identifier: LGPL-2.1-or-later
# Runs every FreeCAD-hosted test and prints a summary. Windows, FreeCAD 1.1.
#   pwsh tests/run_gui_tests.ps1 [-Out <dir>]
param([string]$Out = (Join-Path (Split-Path (Split-Path $PSScriptRoot)) ("_runs\gui_" + (Get-Date -Format "yyyyMMdd_HHmmss"))))

$bin = Join-Path $env:LOCALAPPDATA "Programs\FreeCAD 1.1\bin"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$env:KATYDID_OUT = $Out
Remove-Item Env:KATYDID_EXPERIMENTS -ErrorAction SilentlyContinue

function Invoke-FreeCAD([string]$exe, [string]$script, [string]$phase) {
    $env:KATYDID_PHASE = $phase
    $p = Start-Process (Join-Path $bin $exe) -ArgumentList "`"$script`"" -PassThru -WindowStyle Minimized
    if (-not $p.WaitForExit(180000)) { Stop-Process -Id $p.Id -Force; Write-Warning "$script ($phase) timed out" }
}

Invoke-FreeCAD "freecad.exe" (Join-Path $PSScriptRoot "gui_smoke.py") "smoke"
Invoke-FreeCAD "freecad.exe" (Join-Path $PSScriptRoot "persist_smoke.py") "save"
Invoke-FreeCAD "freecad.exe" (Join-Path $PSScriptRoot "persist_smoke.py") "load"
Invoke-FreeCAD "freecadcmd.exe" (Join-Path $PSScriptRoot "persist_headless.py") "headless"

$failed = 0
foreach ($name in "smoke", "save", "load", "headless") {
    $file = Join-Path $Out "results_$name.json"
    if (-not (Test-Path $file)) { Write-Output "$name : NO RESULTS"; $failed++; continue }
    $r = Get-Content $file -Raw | ConvertFrom-Json
    $bad = @($r.checks.PSObject.Properties | Where-Object { -not $_.Value.ok } | ForEach-Object Name)
    if ($r.exception) { $bad += "exception" }
    Write-Output ("{0,-9}: {1}/{2} passed {3}" -f $name, $r.passed, $r.total, ($bad -join ", "))
    $failed += $bad.Count
}
Write-Output "Output: $Out"
exit [int]($failed -gt 0)
