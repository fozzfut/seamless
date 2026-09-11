# build-fillet-regress.ps1
#
# Compiles repro/cpp/fillet_regress.cpp -- the regression battery for the ChFi3d fix --
# against the OCCT kernel headers. Same rules as build-seam-fillet.ps1: cl.exe is called
# directly, so nothing spawns cmd.exe and no window opens; /MD is mandatory because OCCT
# Release links the dynamic CRT and a second CRT copy would crash on the first exception.
#
# It links against the import libraries of the PRIVATE build tree (build/occt-fix), whose
# sources are C:/dev/occt-fix -- isolated from the shared clone that another agent team is
# editing. Which TKFillet.dll actually runs is decided at run time by PATH, so one binary
# measures both the pristine and the patched kernel.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File build-scripts\build-fillet-regress.ps1

$ErrorActionPreference = 'Stop'

$MSVC   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK    = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER = '10.0.22000.0'
$OCCT   = 'C:\dev\seamless\build\occt-fix'
$OCCTR  = 'C:\dev\seamless\build\occt-release'
$SRC    = 'C:\dev\seamless\repro\cpp\fillet_regress.cpp'
$OUTDIR = 'C:\dev\seamless\build\regress'
$EXE    = Join-Path $OUTDIR 'fillet_regress.exe'

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

$LIBS = @(
  'TKernel.lib','TKMath.lib','TKG2d.lib','TKG3d.lib','TKGeomBase.lib',
  'TKGeomAlgo.lib','TKBRep.lib','TKTopAlgo.lib','TKPrim.lib','TKBO.lib',
  'TKBool.lib','TKShHealing.lib','TKFillet.lib','TKOffset.lib','TKFeat.lib',
  'TKMesh.lib','TKXMesh.lib','TKHLR.lib'
)

Write-Host '=== COMPILE+LINK ==='
$clArgs = @(
  '/nologo','/EHsc','/std:c++17','/MD','/O2','/W3',
  "/I$OCCT\inc",
  $SRC,
  "/Fo:$OUTDIR\", "/Fe:$EXE",
  '/link', "/LIBPATH:$OCCT\win64\vc14\lib", "/LIBPATH:$OCCTR\win64\vc14\lib"
) + $LIBS
Write-Host ('cl.exe ' + ($clArgs -join ' '))
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& cl.exe @clArgs
$rc = $LASTEXITCODE
$sw.Stop()
Write-Host "---- cl EXIT=$rc elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,2)) s ----"
exit $rc
