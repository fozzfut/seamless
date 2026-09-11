# configure-occt-cond.ps1 -- a PRIVATE OCCT 7.8.1 build tree for the "narrowed guard" work.
#
# WHY YET ANOTHER TREE. Three other trees on this machine are owned by other agents and were
# seen changing during measurements:
#   C:/dev/seamless/occt  - shared clone, src/ChFi3d edited (git status: 2 modified files)
#   C:/dev/occt-fix       - another team's private tree
#   C:/dev/occt-e9        - the Edge9 measurement's tree
# Sources here come straight from the tag and are verified against the pristine reference:
#   cd C:/dev/seamless/occt && git archive V7_8_1 | tar -x -C C:/dev/occt-cond
#   md5 src/ChFi3d/ChFi3d_Builder_C1.cxx = 908581ebdfb6dc5fa8914a027299210f
#       == build/occt-src-orig/ChFi3d_Builder_C1.cxx
#
# Options are byte-for-byte those of configure-occt-e9.ps1, so the TKFillet.dll built here is
# interchangeable with the other DLLs of build/occt-release.
$ErrorActionPreference = 'Stop'
$Cmake     = 'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$SourceDir = 'C:/dev/occt-cond'
$BuildDir  = 'C:/dev/seamless/build/occt-cond'
$InstallDir= 'C:/dev/seamless/install/occt-cond'
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
$sw = [Diagnostics.Stopwatch]::StartNew()
Write-Output "=== CONFIGURE: $SourceDir -> $BuildDir ==="
& $Cmake @cmakeArgs
$rc = $LASTEXITCODE
$sw.Stop()
Write-Output ("=== CMAKE EXIT CODE: {0}  WALL {1:N2} s ===" -f $rc, $sw.Elapsed.TotalSeconds)
exit $rc
