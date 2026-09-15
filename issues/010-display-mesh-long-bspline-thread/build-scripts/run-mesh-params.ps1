# run-mesh-params.ps1 -- runs build/mesh-params/mesh_params.exe on the fixture against FreeCAD 1.1.1's own
# OCCT DLLs (PATH puts its bin first). -Quality adds the chord-error sample; -Only picks configurations.
param([string]$FreeCADBin = 'C:\Program Files\FreeCAD 1.1\bin', [switch]$Quality, [string]$Only = '', [int]$Face = 0)
$exe = 'C:\dev\freecad-kernel-fixes\build\mesh-params\mesh_params.exe'
$fixture = Join-Path $PSScriptRoot '..\fixtures\sfu1605_ball_screw.brep'
$env:PATH = "$FreeCADBin;$env:PATH"
if ($Quality) { $env:MESH_QUALITY = '1' }
if ($Only) { $env:MESH_ONLY = $Only }
& $exe $fixture $Face 1
