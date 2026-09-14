# Put the fix of defect 009 (Boolean on a periodic face wider than its period) into a FreeCAD 1.1.1
# installation, check it, and take it out again.
#
#   powershell -ExecutionPolicy Bypass -File install-into-freecad.ps1 -Action status
#   powershell -ExecutionPolicy Bypass -File install-into-freecad.ps1 -Action apply
#   powershell -ExecutionPolicy Bypass -File install-into-freecad.ps1 -Action revert
#   ... -FreeCADDir "C:\dev\fc-gap2\bo"      (any copy; the default is the real installation)
#
# ONE file changes: bin\TKBO.dll. The patched DLL exports the same 966 names as FreeCAD's own, and all
# 892 symbols it imports from 10 OCCT modules are exported by FreeCAD's own DLLs (README.md, section 4).
#
# The script refuses anything it does not recognise by md5: it replaces only FreeCAD 1.1.1's own TKBO.dll
# and restores only from its own backup. FreeCAD must be closed (a loaded DLL cannot be replaced). Writing
# under "C:\Program Files" needs an elevated PowerShell; the script says so instead of failing half way.
# The check runs FreeCADCmd with COPIES of the user's user.cfg / system.cfg and a 120 s deadline.
param(
    [ValidateSet("status", "apply", "revert")]
    [string]$Action = "status",
    [string]$FreeCADDir = "C:\Program Files\FreeCAD 1.1",
    [string]$PatchedDll = "C:\dev\freecad-kernel-fixes\build\occt-bo\win64\vc14\bin\TKBO.dll"
)
$ErrorActionPreference = "Stop"

$STOCK_MD5 = "5983229eb2b6b80ca25019007d2a6c01"     # FreeCAD 1.1.1 (build 20260414) as shipped
$PATCHED_MD5 = "6e31e0e103877eccec25efacd1c602a1"   # V7_8_1 + patches/0001, built in build/occt-bo

$bin = Join-Path $FreeCADDir "bin"
$target = Join-Path $bin "TKBO.dll"
$backup = Join-Path $bin ("TKBO.dll.stock-" + $STOCK_MD5.Substring(0, 8) + ".bak")
$verify = Join-Path $PSScriptRoot "..\repro\python\verify_periodic_pcurve.py"
$report = Join-Path $PSScriptRoot "..\repro\python\verify_periodic_pcurve.txt"
$cmd = Join-Path $bin "FreeCADCmd.exe"

function Md5([string]$path) {
    if (-not (Test-Path $path)) { return "" }
    return (Get-FileHash -Algorithm MD5 $path).Hash.ToLower()
}

function Verdict {
    if (Test-Path $report) { Remove-Item $report }
    $work = Join-Path $env:TEMP ("fc-009-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $cfgDir = Join-Path $env:APPDATA "FreeCAD\v1-1"
    foreach ($name in @("user.cfg", "system.cfg")) {
        $src = Join-Path $cfgDir $name
        if (Test-Path $src) { Copy-Item $src (Join-Path $work $name) }
    }
    $argList = @('-u', ('"' + (Join-Path $work "user.cfg") + '"'), '-s', ('"' + (Join-Path $work "system.cfg") + '"'),
                 ('"' + (Resolve-Path $verify) + '"'))
    $p = Start-Process -FilePath $cmd -ArgumentList $argList -PassThru -WindowStyle Hidden
    $done = $p.WaitForExit(120000)
    if (-not $done) { $p.Kill() }
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
    if (-not $done) { return "PERIODIC-PCURVE: TIMEOUT after 120 s" }
    if (-not (Test-Path $report)) { return "PERIODIC-PCURVE: NO REPORT (FreeCADCmd exit " + $p.ExitCode + ")" }
    $text = Get-Content $report -Encoding UTF8
    $text | Where-Object { $_ -notmatch "^PERIODIC-PCURVE" } | ForEach-Object { Write-Host ("  " + $_) }
    return ($text | Where-Object { $_ -match "^PERIODIC-PCURVE" } | Select-Object -Last 1)
}

function CanWrite([string]$dir) {
    $probe = Join-Path $dir (".write-test-" + [guid]::NewGuid().ToString("N"))
    try { [IO.File]::WriteAllText($probe, "x"); Remove-Item $probe; return $true } catch { return $false }
}

function Running {
    $exe = [IO.Path]::GetFullPath($bin).TrimEnd('\')
    return @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -and ([IO.Path]::GetDirectoryName($_.Path) -ieq $exe) } catch { $false } })
}

if (-not (Test-Path $cmd)) { throw "No FreeCADCmd.exe under $bin" }
$now = Md5 $target
$state = if ($now -eq $STOCK_MD5) { "stock" } elseif ($now -eq $PATCHED_MD5) { "patched" } else { "UNKNOWN" }
Write-Host ("FreeCAD:     " + $FreeCADDir)
Write-Host ("TKBO:        " + $now + "  (" + $state + ")")
Write-Host ("backup:      " + $(if (Test-Path $backup) { $backup + "  md5 " + (Md5 $backup) } else { "none" }))

switch ($Action) {
    "status" {
        Write-Host (Verdict)
    }
    "apply" {
        if ($state -eq "patched") { Write-Host "already patched"; Write-Host (Verdict); break }
        if ($state -ne "stock") { throw "TKBO.dll md5 $now is not FreeCAD 1.1.1's own ($STOCK_MD5): refusing to replace an unknown build" }
        if ((Md5 $PatchedDll) -ne $PATCHED_MD5) { throw "$PatchedDll is not the verified patched build ($PATCHED_MD5)" }
        $running = Running
        if ($running.Count) { throw ("FreeCAD is running from $bin (" + (($running | ForEach-Object { $_.ProcessName + " " + $_.Id }) -join ", ") + "): close it first") }
        if (-not (CanWrite $bin)) { throw "Cannot write to $bin - run this from an elevated PowerShell (Run as administrator)" }
        if (-not (Test-Path $backup)) { Copy-Item $target $backup }
        if ((Md5 $backup) -ne $STOCK_MD5) { throw "the backup $backup does not hold the stock DLL" }
        Copy-Item $PatchedDll $target -Force
        if ((Md5 $target) -ne $PATCHED_MD5) { Copy-Item $backup $target -Force; throw "the copy did not take; the stock DLL was put back" }
        Write-Host "applied; checking the kernel:"
        $v = Verdict
        Write-Host $v
        if ($v -ne "PERIODIC-PCURVE: FIXED") {
            Copy-Item $backup $target -Force
            throw "the kernel did not report FIXED ($v); the stock DLL was put back (md5 $(Md5 $target))"
        }
    }
    "revert" {
        if ($state -eq "stock") { Write-Host "already stock"; Write-Host (Verdict); break }
        if (-not (Test-Path $backup) -or (Md5 $backup) -ne $STOCK_MD5) { throw "no verified stock backup at $backup" }
        $running = Running
        if ($running.Count) { throw "FreeCAD is running from ${bin}: close it first" }
        if (-not (CanWrite $bin)) { throw "Cannot write to $bin - run this from an elevated PowerShell (Run as administrator)" }
        Copy-Item $backup $target -Force
        if ((Md5 $target) -ne $STOCK_MD5) { throw "revert did not take: md5 $(Md5 $target)" }
        Write-Host "reverted; checking the kernel:"
        Write-Host (Verdict)
    }
}
