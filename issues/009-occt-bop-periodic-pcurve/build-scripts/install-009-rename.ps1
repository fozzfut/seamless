# Defect 009 install when zombie FreeCAD processes (unkillable, stuck in the kernel) still map TKBO.dll.
#
#   elevated:  powershell -ExecutionPolicy Bypass -File install-009-rename.ps1 [-FreeCADDir ...] [-Log ...]
#
# A mapped DLL cannot be overwritten, and install-into-freecad.ps1 -Action apply refuses while FreeCAD runs from the
# folder. Windows does allow RENAMING a mapped DLL on the same volume: the stock DLL is moved to the backup name (the
# running processes keep their mapping of it) and the verified patched build is copied in its place. The verdict is
# the issue's own check (install-into-freecad.ps1 -Action status); anything but "PERIODIC-PCURVE: FIXED" - a failed
# check included - puts the stock DLL back. Used on the owner's machine on 15 September 2026.
#
# The first version stopped at the verdict: the status script it called ended with a Remove-Item error on the 8.3 TEMP
# path (fixed there), and in Windows PowerShell 5.1 a native command's stderr redirected with 2>&1 under
# $ErrorActionPreference = "Stop" is thrown as an error. So the patched DLL stayed in place with "EXIT 1" and no
# verdict at all. The check now runs with its own error preference, and its exit code and verdict line are logged.
param(
    [string]$FreeCADDir = (Join-Path $env:ProgramFiles "FreeCAD 1.1"),
    [string]$PatchedDll = "C:\dev\freecad-kernel-fixes\build\occt-bo\win64\vc14\bin\TKBO.dll",
    [string]$Log = "C:\dev\freecad-kernel-fixes\build\install-009-rename.log"
)
$ErrorActionPreference = "Stop"
function L($m) { $m | Out-File -FilePath $Log -Append -Encoding utf8; Write-Host $m }
$STOCK = "5983229eb2b6b80ca25019007d2a6c01"
$PATCHED = "6e31e0e103877eccec25efacd1c602a1"
$bin = Join-Path $FreeCADDir "bin"
$target = Join-Path $bin "TKBO.dll"
$backup = Join-Path $bin ("TKBO.dll.stock-" + $STOCK.Substring(0, 8) + ".bak")
$installer = Join-Path $PSScriptRoot "install-into-freecad.ps1"
function Md5($p) { if (Test-Path -LiteralPath $p) { (Get-FileHash -Algorithm MD5 -LiteralPath $p).Hash.ToLower() } else { "" } }

function Restore-Stock([string]$why) {
    L ("restoring the stock DLL: " + $why)
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
    Move-Item -LiteralPath $backup -Destination $target
    L ("restored, md5 " + (Md5 $target))
}

try {
    L ("started " + (Get-Date -Format s) + " on " + $FreeCADDir)
    L ("target md5 " + (Md5 $target) + ", patched source md5 " + (Md5 $PatchedDll) + ", backup exists " + (Test-Path -LiteralPath $backup))
    if ((Md5 $target) -ne $STOCK) { throw "target is not the stock DLL - refusing" }
    if ((Md5 $PatchedDll) -ne $PATCHED) { throw "source is not the verified patched build - refusing" }
    if (Test-Path -LiteralPath $backup) { throw "a backup file already exists - refusing to overwrite it" }
    Move-Item -LiteralPath $target -Destination $backup
    L ("renamed stock to backup, backup md5 " + (Md5 $backup))
    try {
        Copy-Item -LiteralPath $PatchedDll -Destination $target
        if ((Md5 $target) -ne $PATCHED) { throw "copy did not take" }
        L "patched DLL in place"
    } catch {
        L ("copy failed: " + $_.Exception.Message)
        Restore-Stock "the copy failed"
        throw
    }
    # the verdict: its stderr must not become a terminating error of THIS script (see the header)
    $out = ""
    $code = -1
    $saved = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $installer -Action status -FreeCADDir $FreeCADDir 2>&1 | Out-String
        $code = $LASTEXITCODE
    } catch {
        $out += "check raised: " + $_.Exception.Message
    } finally {
        $ErrorActionPreference = $saved
    }
    L $out
    L ("check exit code " + $code)
    if ($out -notmatch "PERIODIC-PCURVE: FIXED") {
        Restore-Stock "the verdict is not FIXED"
        L "EXIT 2"
        exit 2
    }
    L ("final md5 " + (Md5 $target))
    L "EXIT 0"
} catch {
    L ("ERROR " + $_.Exception.Message)
    L ("final md5 " + (Md5 $target))
    L "EXIT 1"
    exit 1
}
