#!/usr/bin/env bash
# run_case.sh <group> <grid> <case> [deadline_s] [outfile]
#
# Runs ONE OCCT test case in DRAWEXE batch mode (-b: no GUI, no viewer) against the
# private kernel in build/bin-cond, with an explicit deadline: a case that does not
# return is killed and reported as TIMEOUT, which is itself a measurement.
#
# "test" (as opposed to "testgrid") runs the case in THIS process, so anything the
# kernel prints on stdout -- e.g. the SEAMTRACE lines of the instrumented TKFillet --
# lands in the same log, interleaved with the case's own output.
set -u
BIN="${SEAMLESS_BIN:-/c/dev/seamless/build/bin-cond}"
SRC="${SEAMLESS_SRC:-C:/dev/occt-cond}"
GROUP="${1:?usage: run_case.sh <group> <grid> <case> [deadline] [outfile]}"
GRID="${2:?}"
CASE="${3:?}"
DEADLINE="${4:-600}"
OUT="${5:-/dev/stdout}"

export CASROOT="$SRC"
export CSF_OCCTResourcePath="$SRC/src"
export CSF_OCCTDataPath="$SRC/data"
export CSF_TestDataPath="$SRC/data"
export CSF_TestScriptsPath="$SRC/tests"
export DRAWHOME="$BIN/DrawResources"
export DRAWDEFAULT="$BIN/DrawResources/DrawDefault"
export TCL_LIBRARY="C:/Program Files/FreeCAD 1.1/lib/tcl8.6"
export PATH="$BIN:$PATH"

TCL=$(mktemp -t case_XXXXXX.tcl)
printf 'pload TOPTEST\ntest %s %s %s -echo\nputs "SEAMLESS_CASE_DONE"\nexit\n' \
       "$GROUP" "$GRID" "$CASE" > "$TCL"

start=$(date +%s.%N)
timeout -k 10 "$DEADLINE" "$BIN/DRAWEXE.exe" -b -f "$TCL" > "$OUT" 2>&1
rc=$?
end=$(date +%s.%N)
rm -f "$TCL"
awk -v a="$start" -v b="$end" -v r="$rc" -v c="$GROUP/$GRID/$CASE" \
    'BEGIN{printf "RUN %s exit=%d wall=%.3f s\n", c, r, b-a}' >&2
exit $rc
