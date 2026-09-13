#!/usr/bin/env bash
# run_group_data.sh <group> <outdir> <bin-dir>
#
# Same as run_group_cond.sh, but CSF_TestDataPath additionally points at the
# real OCCT test-data repository cloned to C:/dev/occt-dataset, so the cases
# that used to be SKIPPED for want of data actually execute.
#   sources  C:/dev/occt-cond        (git archive V7_8_1, md5-checked)
#   data     C:/dev/occt-cond/data ; C:/dev/occt-dataset
#   kernel   build/bin-stock | build/bin-cond  (the only variable: TKFillet.dll)
set -u
GROUP="${1:?usage: run_group_data.sh <group> <outdir> <bin-dir>}"
OUTDIR="${2:?}"
BIN="${3:?}"
SRC="${SEAMLESS_SRC:-C:/dev/occt-cond}"
DATA="${SEAMLESS_DATA:-C:/dev/occt-dataset}"

export CASROOT="$SRC"
export CSF_OCCTResourcePath="$SRC/src"
export CSF_OCCTDataPath="$SRC/data"
export CSF_TestDataPath="$SRC/data;$DATA"
export CSF_TestScriptsPath="$SRC/tests"
export DRAWHOME="$BIN/DrawResources"
export DRAWDEFAULT="$BIN/DrawResources/DrawDefault"
export TCL_LIBRARY="C:/Program Files/FreeCAD 1.1/lib/tcl8.6"
export PATH="$BIN:$PATH"
export SEAMLESS_GROUP="$GROUP"
export SEAMLESS_OUTDIR="$OUTDIR"
export SEAMLESS_PARALLEL="${SEAMLESS_PARALLEL:-0}"

HERE="$(cd "$(dirname "$0")" && pwd)"
echo "group    = $GROUP"
echo "kernel   = $BIN"
echo "TKFillet = $(md5sum "$BIN/TKFillet.dll" | cut -d' ' -f1)"
echo "data     = $CSF_TestDataPath"
start=$(date +%s.%N)
exec 3>&1
"$BIN/DRAWEXE.exe" -b -f "$HERE/run_group_data.tcl" >&3
rc=$?
end=$(date +%s.%N)
awk -v a="$start" -v b="$end" -v r="$rc" 'BEGIN{printf "GROUP done exit=%d wall=%.1f s\n", r, b-a}'
exit $rc
