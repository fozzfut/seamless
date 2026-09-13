# configure-occt-e9.ps1 -- a PRIVATE OCCT 7.8.1 build tree for the Edge9 measurement.
#
# WHY A SEPARATE TREE. The stock-vs-patched comparison is only worth anything if the two
# kernels differ by the patched line and by nothing else. The trees that already exist on
# this machine cannot give that guarantee:
#   C:/dev/freecad-kernel-fixes/occt      - shared clone, its src/ChFi3d is edited by another agent team
#   C:/dev/occt-fix           - private to that team; a build of theirs was running (13 cl.exe
#                               processes) while this measurement was being set up, and the
#                               TKFillet.dll in its bin directory changed underneath a copy
# So the sources here come straight from the tag:
#   cd C:/dev/freecad-kernel-fixes/occt && git archive V7_8_1 | tar -x -C C:/dev/occt-e9
# verified byte-identical to build/occt-src-orig/ChFi3d_Builder_C1.cxx (md5 908581eb...).
#
# The options are the ones from configure-occt.ps1 -- same generator, same modules, same
# C++ standard -- so the TKFillet.dll built here is interchangeable with the other 17 DLLs
# of build/occt-release (all of which were verified md5-identical to build/variant/pristine).
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File build-scripts\configure-occt-e9.ps1

$ErrorActionPreference = 'Stop'

$Cmake     = 'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$SourceDir = 'C:/dev/occt-e9'
$BuildDir  = 'C:/dev/freecad-kernel-fixes/build/occt-e9'
$InstallDir= 'C:/dev/freecad-kernel-fixes/install/occt-e9'

if (-not (Test-Path $Cmake))                      { throw "cmake not found: $Cmake" }
if (-not (Test-Path "$SourceDir/CMakeLists.txt")) { throw "OCCT sources not found: $SourceDir" }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

$cmakeArgs = @(
  '-S', $SourceDir, '-B', $BuildDir,
  '-G', 'Visual Studio 17 2022', '-A', 'x64',
  '-DCMAKE_CONFIGURATION_TYPES=Release',
  '-DBUILD_LIBRARY_TYPE=Shared',
  '-DBUILD_CPP_STANDARD=C++17',
  "-DINSTALL_DIR=$InstallDir",
  '-D3RDPARTY_DIR=',
  '-DBUILD_MODULE_FoundationClasses=ON',
  '-DBUILD_MODULE_ModelingData=ON',
  '-DBUILD_MODULE_ModelingAlgorithms=ON',
  '-DBUILD_MODULE_Visualization=OFF',
  '-DBUILD_MODULE_ApplicationFramework=OFF',
  '-DBUILD_MODULE_DataExchange=OFF',
  '-DBUILD_MODULE_Draw=OFF',
  '-DBUILD_MODULE_DETools=OFF',
  '-DBUILD_DOC_Overview=OFF',
  '-DBUILD_Inspector=OFF',
  '-DBUILD_SAMPLES_QT=OFF',
  '-DBUILD_SAMPLES_MFC=OFF',
  '-DBUILD_USE_PCH=OFF',
  '-DBUILD_WITH_DEBUG=OFF',
  '-DUSE_FREETYPE=OFF', '-DUSE_TK=OFF', '-DUSE_TCL=OFF',
  '-DUSE_OPENGL=OFF',   '-DUSE_GLES2=OFF', '-DUSE_D3D=OFF', '-DUSE_VTK=OFF',
  '-DUSE_FREEIMAGE=OFF','-DUSE_FFMPEG=OFF','-DUSE_OPENVR=OFF',
  '-DUSE_RAPIDJSON=OFF','-DUSE_DRACO=OFF', '-DUSE_TBB=OFF',  '-DUSE_EIGEN=OFF'
)

Write-Output "=== CONFIGURE: $SourceDir -> $BuildDir ==="
& $Cmake @cmakeArgs
$rc = $LASTEXITCODE
Write-Output "=== CMAKE EXIT CODE: $rc ==="
exit $rc
