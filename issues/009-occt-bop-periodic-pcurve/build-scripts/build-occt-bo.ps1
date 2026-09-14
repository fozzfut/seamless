# build-occt-bo.ps1 -- configure (when needed) and build the private tree build/occt-bo for defect 009.
# Source: C:/dev/freecad-kernel-fixes/occt (tag V7_8_1 plus the patches of this catalogue).
# Only the modules the kernel needs; the configuration is the one of issues/001 (docs/BUILD.md there).
# Usage: powershell -ExecutionPolicy Bypass -File build-occt-bo.ps1 [-Target TKBO] [-Configure]
param([string]$Target = 'TKBO', [switch]$Configure)
$ErrorActionPreference = 'Stop'
$Cmake     = 'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$SourceDir = 'C:/dev/freecad-kernel-fixes/occt'
$BuildDir  = 'C:/dev/freecad-kernel-fixes/build/occt-bo'
$InstallDir= 'C:/dev/freecad-kernel-fixes/install/occt-bo'
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
$sw = [Diagnostics.Stopwatch]::StartNew()
if ($Configure -or -not (Test-Path "$BuildDir/CMakeCache.txt")) {
  $cmakeArgs = @('-S', $SourceDir, '-B', $BuildDir, '-G', 'Visual Studio 17 2022', '-A', 'x64',
    '-DCMAKE_CONFIGURATION_TYPES=Release', '-DBUILD_LIBRARY_TYPE=Shared', '-DBUILD_CPP_STANDARD=C++17',
    "-DINSTALL_DIR=$InstallDir", '-D3RDPARTY_DIR=',
    '-DBUILD_MODULE_FoundationClasses=ON', '-DBUILD_MODULE_ModelingData=ON', '-DBUILD_MODULE_ModelingAlgorithms=ON',
    '-DBUILD_MODULE_Visualization=OFF', '-DBUILD_MODULE_ApplicationFramework=OFF', '-DBUILD_MODULE_DataExchange=OFF',
    '-DBUILD_MODULE_Draw=OFF', '-DBUILD_MODULE_DETools=OFF', '-DBUILD_DOC_Overview=OFF', '-DBUILD_Inspector=OFF',
    '-DBUILD_SAMPLES_QT=OFF', '-DBUILD_SAMPLES_MFC=OFF', '-DBUILD_USE_PCH=OFF', '-DBUILD_WITH_DEBUG=OFF',
    '-DUSE_FREETYPE=OFF', '-DUSE_TK=OFF', '-DUSE_TCL=OFF', '-DUSE_OPENGL=OFF', '-DUSE_GLES2=OFF', '-DUSE_D3D=OFF',
    '-DUSE_VTK=OFF', '-DUSE_FREEIMAGE=OFF', '-DUSE_FFMPEG=OFF', '-DUSE_OPENVR=OFF', '-DUSE_RAPIDJSON=OFF',
    '-DUSE_DRACO=OFF', '-DUSE_TBB=OFF', '-DUSE_EIGEN=OFF')
  & $Cmake @cmakeArgs *> "$BuildDir/configure.log"
  if ($LASTEXITCODE -ne 0) { Write-Output "CONFIGURE EXIT $LASTEXITCODE"; exit $LASTEXITCODE }
  Write-Output ("CONFIGURE EXIT 0 {0:N1} s" -f $sw.Elapsed.TotalSeconds)
}
& $Cmake --build $BuildDir --config Release --parallel 12 --target $Target *> "$BuildDir/build-$Target.log"
$rc = $LASTEXITCODE
Write-Output ("BUILD {0} EXIT {1} WALL {2:N1} s" -f $Target, $rc, $sw.Elapsed.TotalSeconds)
exit $rc
