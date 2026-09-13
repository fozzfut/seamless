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

run() {  # run <label> VAR=value ...
    local label="$1"; shift
    env "$@" timeout -k 5 120 "$FC" "$HERE/rim_fillet_case.py" >/dev/null 2>&1
    [ $? -eq 124 ] && echo "$label TIMEOUT 120 s" >> "$REPORT"
}

echo "TKFillet.dll md5: $(md5sum "$(dirname "$FC")/TKFillet.dll" | cut -c1-8)"
for angle in 0 90; do
    for r in 0.1 0.25 0.5 1.0; do
        run "AngleXU=$angle r=$r" RIM_ANGLE=$angle RIM_R=$r
    done
done
for r in 0.25 0.5 1.0; do
    run "shallower r=$r" RIM_SHALLOWER=1.0 RIM_R=$r
done
cat "$REPORT"
