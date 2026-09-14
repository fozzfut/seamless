# build-repro.ps1 -- compile repro/cpp/periodic_pcurve.cpp against the OCCT 7.8.1 SDK in install/occt-fix
# (real headers and import libraries; TKBO there is built from unpatched BOPTools sources).
# Which TKBO.dll it RUNS with is decided by PATH: run-repro.ps1 runs it twice, stock and patched.
$ErrorActionPreference = 'Stop'
$MSVC   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK    = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER = '10.0.22000.0'
$OCCT   = 'C:/dev/freecad-kernel-fixes/install/occt-fix'
$SRC    = Join-Path $PSScriptRoot '..\repro\cpp\periodic_pcurve.cpp'
$OUTDIR = 'C:\dev\freecad-kernel-fixes\build\periodic-pcurve'
New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null
$env:INCLUDE = @("$MSVC\include","$SDK\Include\$SDKVER\ucrt","$SDK\Include\$SDKVER\um","$SDK\Include\$SDKVER\shared") -join ';'
$env:LIB = @("$MSVC\lib\x64","$SDK\Lib\$SDKVER\ucrt\x64","$SDK\Lib\$SDKVER\um\x64") -join ';'
$env:PATH = "$MSVC\bin\Hostx64\x64;$env:PATH"
$LIBS = @('TKernel.lib','TKMath.lib','TKG2d.lib','TKG3d.lib','TKGeomBase.lib','TKGeomAlgo.lib','TKBRep.lib','TKTopAlgo.lib','TKPrim.lib','TKBO.lib','TKShHealing.lib')
$clArgs = @('/nologo','/EHsc','/std:c++17','/MD','/O2','/W3',"/I$OCCT\inc",$SRC,"/Fo:$OUTDIR\","/Fe:$OUTDIR\periodic_pcurve.exe",'/link',"/LIBPATH:$OCCT\win64\vc14\lib") + $LIBS
& cl.exe @clArgs
exit $LASTEXITCODE
