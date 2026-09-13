# build-edge9.ps1
#
# Compiles repro/cpp/edge9_fillet.cpp against the PRIVATE OCCT 7.8.1 build tree
# C:/dev/freecad-kernel-fixes/build/occt-e9 (see configure-occt-e9.ps1 for why it is private).
#
# The program is linked once and run against two different TKFillet.dll files by changing
# PATH, so the executable is never a variable in the comparison.
#
# Deliberately calls cl.exe directly instead of vcvars64.bat: the environment is set here,
# in PowerShell, so nothing spawns cmd.exe and nothing opens a window -- the owner is asleep.
#
# /MD is mandatory: OCCT Release links the dynamic CRT, and this program catches OCCT
# exceptions, which needs one CRT, not two.
#
# The import libraries are enumerated from the build tree rather than listed by hand: only
# TKFillet and its dependency chain are built there, and a hand-written list would fail on
# the first toolkit that was not needed.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File build-scripts\build-edge9.ps1

$ErrorActionPreference = 'Stop'

$MSVC   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK    = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER = '10.0.22000.0'
$OCCT   = 'C:\dev\freecad-kernel-fixes\build\occt-e9'
$SRC    = 'C:\dev\freecad-kernel-fixes\repro\cpp\edge9_fillet.cpp'
$OUTDIR = 'C:\dev\freecad-kernel-fixes\build\edge9'
$EXE    = Join-Path $OUTDIR 'edge9_fillet.exe'

if (-not (Test-Path "$OCCT\win64\vc14\lib")) { throw "no import libs in $OCCT -- build TKFillet first" }
New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null

$env:INCLUDE = @(
  "$MSVC\include",
  "$SDK\Include\$SDKVER\ucrt",
  "$SDK\Include\$SDKVER\um",
  "$SDK\Include\$SDKVER\shared"
) -join ';'

$env:LIB = @(
  "$MSVC\lib\x64",
  "$SDK\Lib\$SDKVER\ucrt\x64",
  "$SDK\Lib\$SDKVER\um\x64"
) -join ';'

$env:PATH = "$MSVC\bin\Hostx64\x64;$env:PATH"

$LIBS = Get-ChildItem "$OCCT\win64\vc14\lib\*.lib" | ForEach-Object { $_.Name }
Write-Host ("=== LINKING AGAINST {0} import libraries: {1}" -f $LIBS.Count, ($LIBS -join ' '))

$clArgs = @(
  '/nologo','/EHsc','/std:c++17','/MD','/O2','/W3',
  "/I$OCCT\inc",
  $SRC,
  "/Fo:$OUTDIR\", "/Fe:$EXE",
  '/link', "/LIBPATH:$OCCT\win64\vc14\lib"
) + $LIBS

Write-Host '=== COMPILE+LINK ==='
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& cl.exe @clArgs
$rc = $LASTEXITCODE
$sw.Stop()
Write-Host "---- cl EXIT=$rc elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,2)) s ----"
exit $rc
