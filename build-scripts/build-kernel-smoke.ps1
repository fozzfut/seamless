# build-kernel-smoke.ps1
#
# Compiles and links repro/kernel-smoke/kernel_smoke.cpp against the OCCT kernel
# built out of source in C:/dev/seamless/build/occt-release, then runs it.
#
# Deliberately calls cl.exe directly instead of vcvars64.bat: the environment is
# set here, in PowerShell, so nothing spawns cmd.exe and nothing opens a window.
#
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File build-scripts\build-kernel-smoke.ps1

$ErrorActionPreference = 'Stop'

$MSVC    = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK     = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER  = '10.0.22000.0'
$OCCT    = 'C:\dev\seamless\build\occt-release'
$SRC     = 'C:\dev\seamless\repro\kernel-smoke\kernel_smoke.cpp'
$OUTDIR  = 'C:\dev\seamless\build\kernel-smoke'
$EXE     = Join-Path $OUTDIR 'kernel_smoke.exe'

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

$env:PATH = "$MSVC\bin\Hostx64\x64;$OCCT\win64\vc14\bin;$env:PATH"

# The 18 toolkits this kernel build produces. The smoke test only needs
# TKernel TKMath TKG2d TKG3d TKGeomBase TKGeomAlgo TKBRep TKTopAlgo TKPrim
# TKBO TKBool TKShHealing TKFillet; the rest are listed so the line can be
# copied verbatim for bigger programs.
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
  '/link', "/LIBPATH:$OCCT\win64\vc14\lib"
) + $LIBS
Write-Host ('cl.exe ' + ($clArgs -join ' '))
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& cl.exe @clArgs
$rc = $LASTEXITCODE
$sw.Stop()
Write-Host "---- cl EXIT=$rc elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,2)) s ----"
if ($rc -ne 0) { exit $rc }

Write-Host ''
Write-Host '=== RUN ==='
& $EXE (Join-Path $OUTDIR 'kernel_smoke_result.brep')
$rc = $LASTEXITCODE
Write-Host "---- kernel_smoke EXIT=$rc ----"
exit $rc
