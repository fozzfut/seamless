# Runs one FreeCAD process (headless FreeCADCmd or offscreen FreeCAD.exe) with copies of the
# preference files, a private working directory and a hard timeout.
#   run_fc.ps1 -Exe cmd|gui -Script <py> -File <FCStd> -Tag <label> [-Cfg <dir with user.cfg/system.cfg>]
#              [-UserData <dir>] [-TimeoutSec 600] [-Exe2 <FreeCAD bin dir>] [-Env "K=V;K2=V2"]
param(
    [ValidateSet("cmd", "gui")][string]$Exe = "cmd",
    [Parameter(Mandatory = $true)][string]$Script,
    [string]$File = "",
    [Parameter(Mandatory = $true)][string]$Tag,
    [string]$Cfg = "C:\dev\hybriddesign-perf\cfg",
    [string]$UserData = "",
    [int]$TimeoutSec = 600,
    [string]$Bin = "C:\Program Files\FreeCAD 1.1\bin",
    [string]$Env = ""
)
$root = "C:\dev\hybriddesign-perf"
$runDir = Join-Path $root ("runs\" + $Tag)
[System.IO.Directory]::CreateDirectory($runDir) | Out-Null
Copy-Item (Join-Path $Cfg "user.cfg") (Join-Path $runDir "user.cfg") -Force
Copy-Item (Join-Path $Cfg "system.cfg") (Join-Path $runDir "system.cfg") -Force
$out = Join-Path $runDir "result.json"
if (Test-Path $out) { Remove-Item $out }
$log = Join-Path $runDir "fc.log"
if (Test-Path $log) { Remove-Item $log }
$env:PERF_FILE = $File
$env:PERF_OUT = $out
$env:PERF_TAG = $Tag
$env:PERF_RUNDIR = $runDir
$saved = @{}
if ($Env) {
    foreach ($kv in $Env.Split(";")) {
        if (-not $kv) { continue }
        $k, $v = $kv.Split("=", 2)
        $saved[$k] = [Environment]::GetEnvironmentVariable($k)
        [Environment]::SetEnvironmentVariable($k, $v)
    }
}
if ($UserData) { $saved["FREECAD_USER_DATA"] = $env:FREECAD_USER_DATA; $env:FREECAD_USER_DATA = $UserData }
# cache, transient document directories and recovery files go to the run folder, never to the owner's temp
$tempDir = Join-Path $runDir "temp"
[System.IO.Directory]::CreateDirectory($tempDir) | Out-Null
$saved["FREECAD_USER_TEMP"] = $env:FREECAD_USER_TEMP; $env:FREECAD_USER_TEMP = $tempDir
$fcArgs = @("-u", (Join-Path $runDir "user.cfg"), "-s", (Join-Path $runDir "system.cfg"), "--log-file", $log)
if ($Exe -eq "cmd") {
    $exePath = Join-Path $Bin "FreeCADCmd.exe"
    $fcArgs += @($Script)
} else {
    $exePath = Join-Path $Bin "FreeCAD.exe"
    $savedPlat = $env:QT_QPA_PLATFORM
    $env:QT_QPA_PLATFORM = "offscreen"
    $fcArgs += @($Script)
}
$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process -FilePath $exePath -ArgumentList $fcArgs -PassThru -WorkingDirectory $runDir -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $runDir "stdout.txt") -RedirectStandardError (Join-Path $runDir "stderr.txt")
$ok = $p.WaitForExit($TimeoutSec * 1000)
if (-not $ok) { try { $p.Kill() } catch {}; Write-Host "TIMEOUT $Tag after $TimeoutSec s" }
$sw.Stop()
if ($Exe -eq "gui") { $env:QT_QPA_PLATFORM = $savedPlat }
foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
Write-Host ("[{0}] exit={1} process_wall={2:N2}s" -f $Tag, $(if ($ok) { $p.ExitCode } else { "killed" }), $sw.Elapsed.TotalSeconds)
Get-Content (Join-Path $runDir "stdout.txt") -ErrorAction SilentlyContinue | Where-Object { $_ -match "PERF" } | ForEach-Object { Write-Host $_ }

