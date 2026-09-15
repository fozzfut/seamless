# Defect 009 regression run on ONE FreeCAD installation: FreeCAD's own test suites, the Boolean fuzz and the issue's
# two repros, every result into -Out. Run it on the patched installation and on one that differs from it only in
# TKBO.dll, then compare (FreeCAD's bin\python.exe is enough):
#
#   powershell -ExecutionPolicy Bypass -File run_regression.ps1 -FreeCADDir "C:\Program Files\FreeCAD 1.1" -Out C:\dev\...\patched
#   powershell -ExecutionPolicy Bypass -File run_regression.ps1 -FreeCADDir C:\dev\fc-gap2\patched -Out C:\dev\...\stock
#   python compare_suites.py C:\dev\...\stock C:\dev\...\patched
#   python compare_fuzz.py C:\dev\...\stock\fuzz.jsonl C:\dev\...\patched\fuzz.jsonl
#
#   -Steps suites,fuzz,python,cpp   (default: all four)     -Suites TestPartApp,...     -TimeoutSeconds 900 per process
#
# Every FreeCADCmd gets its own COPIES of user.cfg and system.cfg (-u, -s) under <Out>\cfg\<step>, TEMP and its working
# directory under <Out>\tmp, and a deadline after which its process tree is killed. -Out must be an ASCII path: FreeCAD
# cannot open a Cyrillic one. The Python repro (repro/python/verify_periodic_pcurve.py) writes its report next to
# itself, so it runs from a byte copy under <Out>\repro-copy with the fixture at the same relative place - two runs at
# once cannot overwrite each other's report and the repository file stays as it is. The C++ repro
# (build\periodic-pcurve\periodic_pcurve.exe, build-scripts\build-repro.ps1) finds its OCCT DLLs on PATH: <FreeCADDir>\bin
# is put first, so it runs on that installation's TKBO.dll.
param(
    [Parameter(Mandatory = $true)][string]$FreeCADDir,
    [Parameter(Mandatory = $true)][string]$Out,
    [string[]]$Steps = @("suites", "fuzz", "python", "cpp"),
    [string[]]$Suites = @("TestPartApp", "TestPartDesignApp", "TestSketcherApp", "TestOpenSCADApp"),
    [int]$TimeoutSeconds = 900,
    [string]$ConfigDir = (Join-Path $env:APPDATA "FreeCAD\v1-1"),
    [string]$CppRepro = "C:\dev\freecad-kernel-fixes\build\periodic-pcurve\periodic_pcurve.exe"
)
$ErrorActionPreference = "Stop"
# powershell -File hands "-Steps fuzz,python" over as ONE string (measured: no step ran); split it here
$Steps = @($Steps | ForEach-Object { $_ -split "," } | Where-Object { $_ })
$Suites = @($Suites | ForEach-Object { $_ -split "," } | Where-Object { $_ })
$issue = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $FreeCADDir "bin"
$cmd = Join-Path $bin "FreeCADCmd.exe"
if (-not (Test-Path -LiteralPath $cmd)) { throw "no FreeCADCmd.exe under $bin" }
if ($Out -match "[^\x00-\x7F]") { throw "-Out $Out is not an ASCII path: FreeCAD cannot open it" }
[IO.Directory]::CreateDirectory($Out) | Out-Null
$tmp = Join-Path $Out "tmp"
[IO.Directory]::CreateDirectory($tmp) | Out-Null
$env:TEMP = $tmp
$env:TMP = $tmp
$summary = Join-Path $Out "summary.txt"

function Md5([string]$p) {
    if (Test-Path -LiteralPath $p) { return (Get-FileHash -Algorithm MD5 -LiteralPath $p).Hash.ToLower() }
    return "absent"
}

function Note([string]$line) {
    Write-Host $line
    Add-Content -LiteralPath $summary -Value $line -Encoding UTF8
}

function Invoke-Process([string]$name, [string]$exe, [string[]]$arguments) {
    $log = Join-Path $Out ($name + ".out.txt")
    $err = Join-Path $Out ($name + ".err.txt")
    $started = Get-Date
    $how = @{ FilePath = $exe; WorkingDirectory = $tmp; RedirectStandardOutput = $log; RedirectStandardError = $err
              PassThru = $true; NoNewWindow = $true }
    $quoted = @($arguments | Where-Object { $_ } | ForEach-Object { if ($_ -match "\s") { '"' + $_ + '"' } else { $_ } })
    if ($quoted.Count) { $how.ArgumentList = $quoted }     # Start-Process refuses an empty -ArgumentList (measured)
    $p = Start-Process @how
    $null = $p.Handle      # Windows PowerShell 5.1 loses ExitCode unless the handle is taken before the wait
    $done = $p.WaitForExit($TimeoutSeconds * 1000)
    if (-not $done) { & taskkill.exe /PID $p.Id /T /F | Out-Null; $p.WaitForExit() }
    $seconds = ((Get-Date) - $started).TotalSeconds
    $code = if ($done) { $p.ExitCode } else { "killed after $TimeoutSeconds s" }
    Note ("{0}: exit {1}, {2:N1} s" -f $name, $code, $seconds)
}

function Invoke-FreeCAD([string]$name, [string[]]$arguments) {
    $cfg = Join-Path $Out ("cfg\" + $name)
    [IO.Directory]::CreateDirectory($cfg) | Out-Null
    foreach ($f in @("user.cfg", "system.cfg")) {
        $src = Join-Path $ConfigDir $f
        if (Test-Path -LiteralPath $src) { [IO.File]::Copy($src, (Join-Path $cfg $f), $true) }
    }
    Invoke-Process $name $cmd (@("-u", (Join-Path $cfg "user.cfg"), "-s", (Join-Path $cfg "system.cfg")) + $arguments)
}

Note ("run_regression {0}  FreeCAD {1}  TKBO.dll {2}  TKFillet.dll {3}  steps {4}" -f (Get-Date -Format s), $FreeCADDir,
      (Md5 (Join-Path $bin "TKBO.dll")), (Md5 (Join-Path $bin "TKFillet.dll")), ($Steps -join ","))

if ($Steps -contains "suites") {
    foreach ($suite in $Suites) { Invoke-FreeCAD ("suite-" + $suite) @("-t", $suite) }
}
if ($Steps -contains "fuzz") {
    $env:FUZZ_OUT = Join-Path $Out "fuzz.jsonl"
    Invoke-FreeCAD "fuzz" @((Join-Path $PSScriptRoot "boolean_fuzz.py"))
    Remove-Item Env:FUZZ_OUT
}
if ($Steps -contains "python") {
    $copy = Join-Path $Out "repro-copy"
    foreach ($d in @("repro\python", "fixtures")) { [IO.Directory]::CreateDirectory((Join-Path $copy $d)) | Out-Null }
    $script = Join-Path $copy "repro\python\verify_periodic_pcurve.py"
    [IO.File]::Copy((Join-Path $issue "repro\python\verify_periodic_pcurve.py"), $script, $true)
    [IO.File]::Copy((Join-Path $issue "fixtures\periodic_overshoot_cylinder.brep"),
                    (Join-Path $copy "fixtures\periodic_overshoot_cylinder.brep"), $true)
    Note ("python-repro: script md5 {0} (repository {1})" -f (Md5 $script), (Md5 (Join-Path $issue "repro\python\verify_periodic_pcurve.py")))
    Invoke-FreeCAD "python-repro" @($script)
    $report = Join-Path $copy "repro\python\verify_periodic_pcurve.txt"
    if (Test-Path -LiteralPath $report) {
        [IO.File]::Copy($report, (Join-Path $Out "python-repro.txt"), $true)
        Note ("python-repro: " + ((Get-Content -LiteralPath $report | Where-Object { $_ -match "^PERIODIC-PCURVE" }) -join " "))
    } else {
        Note "python-repro: no report"
    }
}
if ($Steps -contains "cpp") {
    if (-not (Test-Path -LiteralPath $CppRepro)) { throw "no C++ repro at $CppRepro (build-scripts\build-repro.ps1)" }
    $savedPath = $env:PATH
    try {
        $env:PATH = $bin + ";" + $savedPath
        Invoke-Process "cpp-repro" $CppRepro @()
    } finally {
        $env:PATH = $savedPath
    }
    $text = Get-Content -LiteralPath (Join-Path $Out "cpp-repro.out.txt")
    Note ("cpp-repro: " + (($text | Where-Object { $_ -match "^PERIODIC-PCURVE|^OCCT " }) -join " | "))
}
