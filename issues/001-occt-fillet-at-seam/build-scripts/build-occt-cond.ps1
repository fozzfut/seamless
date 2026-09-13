# build-occt-cond.ps1 -- build the private tree C:/dev/freecad-kernel-fixes/build/occt-cond.
# Optional -Target builds one toolkit only (e.g. TKFillet, ~15 s) instead of everything.
param([string]$Target = '')
$ErrorActionPreference = 'Stop'
$Cmake    = 'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$BuildDir = 'C:/dev/freecad-kernel-fixes/build/occt-cond'
$Log      = "$BuildDir/build.log"
$Status   = "$BuildDir/build.status"
$args = @('--build', $BuildDir, '--config', 'Release', '--parallel', '12')
if ($Target -ne '') { $args += @('--target', $Target) }
"START $(Get-Date -Format o) TARGET=$Target" | Out-File -Encoding utf8 $Status
$sw = [Diagnostics.Stopwatch]::StartNew()
& $Cmake @args *> $Log
$rc = $LASTEXITCODE
$sw.Stop()
Add-Content -Encoding utf8 $Status ("EXIT {0} WALL {1:N2} s FINISH {2}" -f $rc, $sw.Elapsed.TotalSeconds, (Get-Date -Format o))
exit $rc
