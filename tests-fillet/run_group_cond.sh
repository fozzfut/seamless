#!/usr/bin/env bash
# run_group_cond.sh <group> <outdir> [bin-dir]
#
# Same as run_suite.sh, but against the PRIVATE tree of the narrowed-guard work:
#   sources  C:/dev/occt-cond            (git archive V7_8_1, md5-checked)
#   kernel   build/bin-cond | build/bin-stock  (the only variable: TKFillet.dll)
# testgrid gives every case its own DRAWEXE process, and tests/blend/begin sets
# cpulimit 600, so a hung fillet is killed and recorded instead of stopping the run.
set -u
GROUP="${1:?usage: run_group_cond.sh <group> <outdir> [bin-dir]}"
OUTDIR="${2:?}"
BIN="${3:-/c/dev/seamless/build/bin-cond}"
SRC="${SEAMLESS_SRC:-C:/dev/occt-cond}"

export CASROOT="$SRC"
export CSF_OCCTResourcePath="$SRC/src"
export CSF_OCCTDataPath="$SRC/data"
export CSF_TestDataPath="$SRC/data"
export CSF_TestScriptsPath="$SRC/tests${SEAMLESS_EXTRA_SCRIPTS:+;$SEAMLESS_EXTRA_SCRIPTS}"
export DRAWHOME="$BIN/DrawResources"
export DRAWDEFAULT="$BIN/DrawResources/DrawDefault"
export TCL_LIBRARY="C:/Program Files/FreeCAD 1.1/lib/tcl8.6"
export PATH="$BIN:$PATH"
export SEAMLESS_GROUP="$GROUP"
export SEAMLESS_OUTDIR="$OUTDIR"

HERE="$(cd "$(dirname "$0")" && pwd)"
echo "kernel   = $BIN"
echo "TKFillet = $(md5sum "$BIN/TKFillet.dll" | cut -d' ' -f1)"
start=$(date +%s.%N)
exec 3>&1
"$BIN/DRAWEXE.exe" -b -f "$HERE/run_group.tcl" >&3
rc=$?
end=$(date +%s.%N)
awk -v a="$start" -v b="$end" -v r="$rc" 'BEGIN{printf "GROUP done exit=%d wall=%.1f s\n", r, b-a}'
exit $rc
