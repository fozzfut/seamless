# verify-fixed-kernel.ps1
#
# Proves that the FIXED kernel is a kernel one can actually build on: it compiles the
# reproduction program against the SELF-CONTAINED install at C:\dev\seamless\install\occt-fix
# -- real headers, real import libraries, nothing pointing back into a source tree -- and
# then runs it with only that install's bin on PATH.
#
# The point of going through the install rather than the build tree: build/occt-fix/inc
# holds FORWARDER headers, one-line files that #include out of C:/dev/occt-fix/src. Anything
# compiled against those breaks the day that source tree moves. The install directory has
# 3656 real header files and depends on nothing outside itself.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File build-scripts\verify-fixed-kernel.ps1

$ErrorActionPreference = 'Stop'

$MSVC   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK    = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER = '10.0.22000.0'
$KERNEL = 'C:\dev\seamless\install\occt-fix'
$SRC    = 'C:\dev\seamless\repro\cpp\seam_fillet.cpp'
$OUTDIR = 'C:\dev\seamless\build\verify-fixed'
$EXE    = Join-Path $OUTDIR 'seam_fillet_fixed.exe'

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

Write-Host '=== COMPILE against the installed fixed kernel ==='
$clArgs = @(
  '/nologo','/EHsc','/std:c++17','/MD','/O2','/W3',
  "/I$KERNEL\inc",
  $SRC,
  "/Fo:$OUTDIR\", "/Fe:$EXE",
  '/link', "/LIBPATH:$KERNEL\win64\vc14\lib"
) + $LIBS
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& cl.exe @clArgs
$rc = $LASTEXITCODE
$sw.Stop()
Write-Host "---- cl EXIT=$rc elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,2)) s ----"
if ($rc -ne 0) { exit $rc }

# Run with ONLY the installed kernel plus System32 visible. If a DLL were missing the
# program would fail to start rather than quietly pick up some other copy of OCCT.
Write-Host ''
Write-Host '=== RUN with only the installed kernel on PATH ==='
$env:PATH = "$KERNEL\win64\vc14\bin;$env:SystemRoot\System32"
Write-Host "PATH = $env:PATH"
Write-Host ''
Write-Host '--- seam far from the spine vertex (this always worked) ---'
& $EXE --case --rot 0 --radius 1.0
Write-Host ''
Write-Host '--- seam exactly ON the spine vertex (this is the defect) ---'
& $EXE --case --rot 270 --radius 1.0
exit $LASTEXITCODE
