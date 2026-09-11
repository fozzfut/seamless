# rebuild-occt-cond-clean.ps1 -- wipe every compiled artefact of the PRIVATE tree
# C:/dev/seamless/build/occt-cond and build it again from the sources in
# C:/dev/occt-cond, so that every DLL measured afterwards demonstrably comes from
# this session and from this source tree.  Times the clean and the build separately
# and records free disk before and after; a build is not a measurement without them.
$ErrorActionPreference = 'Stop'
$Cmake    = 'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$BuildDir = 'C:/dev/seamless/build/occt-cond'
$Log      = "$BuildDir/rebuild.log"
$Status   = "$BuildDir/rebuild.status"
function FreeMB { [math]::Round((Get-PSDrive C).Free / 1MB, 0) }
"START $(Get-Date -Format o) FREE_MB_BEFORE $(FreeMB)" | Out-File -Encoding utf8 $Status
$sw = [Diagnostics.Stopwatch]::StartNew()
& $Cmake --build $BuildDir --config Release --target clean *> $Log
$rcClean = $LASTEXITCODE
$tClean = $sw.Elapsed.TotalSeconds
Add-Content -Encoding utf8 $Status ("CLEAN EXIT {0} WALL {1:N2} s FREE_MB_AFTER_CLEAN {2}" -f $rcClean, $tClean, (FreeMB))
$sw2 = [Diagnostics.Stopwatch]::StartNew()
& $Cmake --build $BuildDir --config Release --parallel 12 *>> $Log
$rc = $LASTEXITCODE
$sw2.Stop()
Add-Content -Encoding utf8 $Status ("BUILD EXIT {0} WALL {1:N2} s FREE_MB_AFTER {2} FINISH {3}" -f $rc, $sw2.Elapsed.TotalSeconds, (FreeMB), (Get-Date -Format o))
exit $rc
