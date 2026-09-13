# Put the seam-fillet fix into a FreeCAD 1.1.1 installation, check it, and take it out again.
#
#   powershell -ExecutionPolicy Bypass -File install-into-freecad.ps1 -Action status
#   powershell -ExecutionPolicy Bypass -File install-into-freecad.ps1 -Action apply
#   powershell -ExecutionPolicy Bypass -File install-into-freecad.ps1 -Action revert
#   ... -FreeCADDir "C:\dev\fc-gap2\stock"      (any copy; the default is the real installation)
#
# ONE file changes: bin\TKFillet.dll. Why one is enough is proven in docs/IN_FREECAD.md, section 1:
# all 1065 imports of the patched DLL are exported by FreeCAD's own modules, all 586 symbols the
# 12 consumers in the installation take from TKFillet are exported by the patched DLL, and the
# two export tables are identical (1380 = 1380).
#
# The script refuses anything it does not recognise by md5: it replaces only FreeCAD 1.1.1's own
# TKFillet.dll and restores only from its own backup, so it cannot stack on an unknown build.
# Writing under "C:\Program Files" needs an elevated PowerShell; the script says so instead of
# failing half way. Every FreeCADCmd run it makes has a 120 s deadline.
param(
    [ValidateSet("status", "apply", "revert")]
    [string]$Action = "status",
    [string]$FreeCADDir = "C:\Program Files\FreeCAD 1.1",
    [string]$PatchedDll = "C:\dev\seamless\build\bin-cond\TKFillet.dll"
)
$ErrorActionPreference = "Stop"

$STOCK_MD5 = "6d9915afa227e9bff7c0c2cc29806cd3"     # FreeCAD 1.1.1 (build 20260414) as shipped
$PATCHED_MD5 = "4e89e519f8a7ec7f7ed7f2b198d60275"   # V7_8_1 + patches/0002, built in build/occt-cond

$bin = Join-Path $FreeCADDir "bin"
$target = Join-Path $bin "TKFillet.dll"
$backup = Join-Path $bin ("TKFillet.dll.stock-" + $STOCK_MD5.Substring(0, 8) + ".bak")
$verify = Join-Path $PSScriptRoot "verify-seam-fillet.py"
$cmd = Join-Path $bin "FreeCADCmd.exe"

function Md5([string]$path) {
    if (-not (Test-Path $path)) { return "" }
    return (Get-FileHash -Algorithm MD5 $path).Hash.ToLower()
}

function Verdict {
    $report = Join-Path $PSScriptRoot "verify-seam-fillet.txt"
    if (Test-Path $report) { Remove-Item $report }
    $p = Start-Process -FilePath $cmd -ArgumentList ('"' + $verify + '"') -PassThru -WindowStyle Hidden
    if (-not $p.WaitForExit(120000)) { $p.Kill(); return "SEAM-FILLET: TIMEOUT after 120 s" }
    if (-not (Test-Path $report)) { return "SEAM-FILLET: NO REPORT (FreeCADCmd exit " + $p.ExitCode + ")" }
    $text = Get-Content $report -Encoding UTF8
    $text | Where-Object { $_ -notmatch "^SEAM-FILLET" } | ForEach-Object { Write-Host ("  " + $_) }
    return ($text | Where-Object { $_ -match "^SEAM-FILLET" } | Select-Object -Last 1)
}

function CanWrite([string]$dir) {
    $probe = Join-Path $dir (".write-test-" + [guid]::NewGuid().ToString("N"))
    try { [IO.File]::WriteAllText($probe, "x"); Remove-Item $probe; return $true } catch { return $false }
}

if (-not (Test-Path $cmd)) { throw "No FreeCADCmd.exe under $bin" }
$now = Md5 $target
$state = if ($now -eq $STOCK_MD5) { "stock" } elseif ($now -eq $PATCHED_MD5) { "patched" } else { "UNKNOWN" }
Write-Host ("FreeCAD:     " + $FreeCADDir)
Write-Host ("TKFillet:    " + $now + "  (" + $state + ")")
Write-Host ("backup:      " + $(if (Test-Path $backup) { $backup + "  md5 " + (Md5 $backup) } else { "none" }))

switch ($Action) {
    "status" {
        Write-Host (Verdict)
    }
    "apply" {
        if ($state -eq "patched") { Write-Host "already patched"; Write-Host (Verdict); break }
        if ($state -ne "stock") { throw "TKFillet.dll md5 $now is not FreeCAD 1.1.1's own ($STOCK_MD5): refusing to replace an unknown build" }
        if ((Md5 $PatchedDll) -ne $PATCHED_MD5) { throw "$PatchedDll is not the verified patched build ($PATCHED_MD5)" }
        if (-not (CanWrite $bin)) { throw "Cannot write to $bin - run this from an elevated PowerShell (Run as administrator)" }
        if (-not (Test-Path $backup)) { Copy-Item $target $backup }
        if ((Md5 $backup) -ne $STOCK_MD5) { throw "the backup $backup does not hold the stock DLL" }
        Copy-Item $PatchedDll $target -Force
        if ((Md5 $target) -ne $PATCHED_MD5) { Copy-Item $backup $target -Force; throw "the copy did not take; the stock DLL was put back" }
        Write-Host "applied; checking the kernel:"
        $v = Verdict
        Write-Host $v
        if ($v -ne "SEAM-FILLET: FIXED") {
            Copy-Item $backup $target -Force
            throw "the kernel did not report FIXED ($v); the stock DLL was put back (md5 $(Md5 $target))"
        }
    }
    "revert" {
        if ($state -eq "stock") { Write-Host "already stock"; Write-Host (Verdict); break }
        if (-not (Test-Path $backup) -or (Md5 $backup) -ne $STOCK_MD5) { throw "no verified stock backup at $backup" }
        if (-not (CanWrite $bin)) { throw "Cannot write to $bin - run this from an elevated PowerShell (Run as administrator)" }
        Copy-Item $backup $target -Force
        if ((Md5 $target) -ne $STOCK_MD5) { throw "revert did not take: md5 $(Md5 $target)" }
        Write-Host "reverted; checking the kernel:"
        Write-Host (Verdict)
    }
}
