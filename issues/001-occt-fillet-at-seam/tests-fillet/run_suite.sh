#!/bin/bash
# usage: run_suite.sh <group> <outdir>
# Runs one OCCT test group in DRAWEXE batch mode (-b: no GUI, no viewers).
# The kernel under test is whatever TKFillet.dll currently sits in BIN.
# Working directory holding the private DRAWHOME and the generated group.
# Set SEAMLESS_SCRATCH to point at it.
SP="${SEAMLESS_SCRATCH:?set SEAMLESS_SCRATCH to the scratch dir (see docs/REGRESSION.md)}"
BIN="${SEAMLESS_BIN:-/c/dev/freecad-kernel-fixes/build/occt-release/win64/vc14/bin}"
export CASROOT="C:/dev/freecad-kernel-fixes/occt"
export CSF_OCCTResourcePath="C:/dev/freecad-kernel-fixes/occt/src"
export CSF_OCCTDataPath="C:/dev/freecad-kernel-fixes/occt/data"
export CSF_TestDataPath="C:/dev/freecad-kernel-fixes/occt/data"
# both the stock OCCT groups and the generated "seamless" group
export CSF_TestScriptsPath="C:/dev/freecad-kernel-fixes/occt/tests;$SP/tests"
export DRAWHOME="$SP/DrawResources"
export DRAWDEFAULT="$SP/DrawResources/DrawDefault"
export TCL_LIBRARY="C:/Program Files/FreeCAD 1.1/lib/tcl8.6"
# tcl86t.dll is copied into BIN, so one PATH entry suffices (a Windows-style
# path inside a colon-separated MSYS PATH would be split on its drive colon).
export PATH="$BIN:$PATH"
export SEAMLESS_GROUP="$1"
export SEAMLESS_OUTDIR="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
exec "$BIN/DRAWEXE.exe" -b -f "${SEAMLESS_RUNNER:-$HERE/run_group.tcl}"
