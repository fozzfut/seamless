# configure-occt.ps1 - конфигурация OCCT 7.8.1 под ядро для собственного CAD-приложения.
# Сборка ВНЕ исходников: исходники C:/dev/seamless/occt не изменяются.
# Запуск:  powershell -ExecutionPolicy Bypass -File C:\dev\seamless\build-scripts\configure-occt.ps1
# Повторный запуск безопасен: CMake просто переконфигурирует дерево.

$ErrorActionPreference = 'Stop'

$Cmake     = 'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$SourceDir = 'C:/dev/seamless/occt'
$BuildDir  = 'C:/dev/seamless/build/occt-release'
$InstallDir= 'C:/dev/seamless/install/occt-7.8.1'

if (-not (Test-Path $Cmake))                       { throw "cmake не найден: $Cmake" }
if (-not (Test-Path "$SourceDir/CMakeLists.txt"))  { throw "исходники OCCT не найдены: $SourceDir" }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

$cmakeArgs = @(
  '-S', $SourceDir,
  '-B', $BuildDir,
  '-G', 'Visual Studio 17 2022',
  '-A', 'x64',

  # --- тип сборки ---------------------------------------------------------
  '-DCMAKE_CONFIGURATION_TYPES=Release',   # только Release: Debug удвоил бы диск
  '-DBUILD_LIBRARY_TYPE=Shared',           # DLL + import .lib - то, на что линкуется приложение
  '-DBUILD_CPP_STANDARD=C++17',
  "-DINSTALL_DIR=$InstallDir",
  '-D3RDPARTY_DIR=',

  # --- модули ЯДРА (нужны) -----------------------------------------------
  '-DBUILD_MODULE_FoundationClasses=ON',   # TKernel, TKMath
  '-DBUILD_MODULE_ModelingData=ON',        # TKG2d TKG3d TKGeomBase TKBRep - топология, pcurves, шов
  '-DBUILD_MODULE_ModelingAlgorithms=ON',  # TKFillet (скругление), TKBO/TKBool, TKPrim, TKShHealing

  # --- модули, выключенные осознанно --------------------------------------
  '-DBUILD_MODULE_Visualization=OFF',      # требует FreeType (нет заголовков на машине)
  '-DBUILD_MODULE_ApplicationFramework=OFF',
  '-DBUILD_MODULE_DataExchange=OFF',       # тянет TKXCAF -> TKV3d/TKService -> FreeType
  '-DBUILD_MODULE_Draw=OFF',               # требует Tcl/Tk
  '-DBUILD_MODULE_DETools=OFF',
  '-DBUILD_DOC_Overview=OFF',
  '-DBUILD_Inspector=OFF',
  '-DBUILD_SAMPLES_QT=OFF',
  '-DBUILD_SAMPLES_MFC=OFF',
  '-DBUILD_USE_PCH=OFF',
  '-DBUILD_WITH_DEBUG=OFF',

  # --- сторонние библиотеки: всё выключено, ничего не ищем ----------------
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
