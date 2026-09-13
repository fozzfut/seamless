#!/usr/bin/env bash
# runone.sh <group> <grid> <case> <bin> <outfile>
set -u
SRC=C:/dev/occt-cond
export CASROOT="$SRC" CSF_OCCTResourcePath="$SRC/src" CSF_OCCTDataPath="$SRC/data"
export CSF_TestDataPath="$SRC/data;C:/dev/occt-dataset" CSF_TestScriptsPath="$SRC/tests"
export DRAWHOME="$4/DrawResources" DRAWDEFAULT="$4/DrawResources/DrawDefault"
export TCL_LIBRARY="C:/Program Files/FreeCAD 1.1/lib/tcl8.6"
export PATH="$4:$PATH"
export SEAMLESS_G="$1" SEAMLESS_GRID="$2" SEAMLESS_CASE="$3" SEAMLESS_OUTFILE="$5"
mkdir -p "$(dirname "$5")"
"$4/DRAWEXE.exe" -b -f "$(dirname "$0")/run_one_case.tcl" >/dev/null 2>&1
