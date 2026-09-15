# build-mesh-params.ps1 -- compile repro/cpp/mesh_params.cpp against the OCCT 7.8.1 SDK in install/occt-fix.
# It RUNS against whichever TKMesh.dll comes first in PATH; run-mesh-params.ps1 puts FreeCAD 1.1.1's bin first.
$ErrorActionPreference = 'Stop'
$MSVC   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK    = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER = '10.0.22000.0'
$OCCT   = 'C:/dev/freecad-kernel-fixes/install/occt-fix'
$SRC    = Join-Path $PSScriptRoot '..\repro\cpp\mesh_params.cpp'
$OUTDIR = 'C:\dev\freecad-kernel-fixes\build\mesh-params'
New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null
$env:INCLUDE = @("$MSVC\include","$SDK\Include\$SDKVER\ucrt","$SDK\Include\$SDKVER\um","$SDK\Include\$SDKVER\shared") -join ';'
$env:LIB = @("$MSVC\lib\x64","$SDK\Lib\$SDKVER\ucrt\x64","$SDK\Lib\$SDKVER\um\x64") -join ';'
$env:PATH = "$MSVC\bin\Hostx64\x64;$env:PATH"
$LIBS = @('TKernel.lib','TKMath.lib','TKG2d.lib','TKG3d.lib','TKGeomBase.lib','TKGeomAlgo.lib','TKBRep.lib','TKTopAlgo.lib','TKMesh.lib')
$clArgs = @('/nologo','/EHsc','/std:c++17','/MD','/O2','/W3','/D_USE_MATH_DEFINES',"/I$OCCT\inc",$SRC,"/Fo:$OUTDIR\","/Fe:$OUTDIR\mesh_params.exe",'/link',"/LIBPATH:$OCCT\win64\vc14\lib") + $LIBS
& cl.exe @clArgs
exit $LASTEXITCODE
