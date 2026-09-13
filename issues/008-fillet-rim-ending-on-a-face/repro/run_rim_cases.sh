#!/usr/bin/env bash
# All cases of issue 008, each in its own FreeCADCmd process with a 120 s deadline.
#
#   bash run_rim_cases.sh ["<FreeCAD>/bin/FreeCADCmd.exe"]
#
# Prints the table to stdout; a case that hits the deadline prints TIMEOUT instead of hanging the run.
FC="${1:-C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPORT="$(python -c 'import tempfile, os; print(os.path.join(tempfile.gettempdir(), "rim_fillet_cases.txt"))')"
rm -f "$REPORT"

run() {  # run <script> <label> VAR=value ...
    local script="$1" label="$2"; shift 2
    env "$@" timeout -k 5 120 "$FC" "$HERE/$script" >/dev/null 2>&1
    [ $? -eq 124 ] && echo "$label TIMEOUT 120 s" >> "$REPORT"
}

echo "TKFillet.dll md5: $(md5sum "$(dirname "$FC")/TKFillet.dll" | cut -c1-8)"
for angle in 0 90; do
    for r in 0.1 0.25 0.5 1.0; do
        run rim_fillet_case.py "AngleXU=$angle r=$r" RIM_ANGLE=$angle RIM_R=$r
    done
done
for r in 0.25 0.5 1.0; do
    run rim_fillet_case.py "shallower r=$r" RIM_SHALLOWER=1.0 RIM_R=$r
done
# The workaround: the fillet built as a ring. Control first (the kernel can fillet it), then the part.
for r in 0.25 0.5 1.0; do
    run ring_fillet_case.py "ring shallower r=$r" RIM_SHALLOWER=1.0 RIM_R=$r
done
for r in 0.25 0.3 0.35 0.5 1.0 2.0; do
    run ring_fillet_case.py "ring r=$r" RIM_ROUTE=extend RIM_R=$r
done
cat "$REPORT"
