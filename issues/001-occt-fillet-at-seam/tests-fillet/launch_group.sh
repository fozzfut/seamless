#!/usr/bin/env bash
# launch one group x kernel run in its own cwd
set -u
G="$1"; K="$2"; R="$3"
d="$R/$G-$K"; mkdir -p "$d/out"
cd "$d"
/c/dev/freecad-kernel-fixes/issues/001-occt-fillet-at-seam/tests-fillet/run_group_data.sh "$G" "$d/out" "/c/dev/freecad-kernel-fixes/build/bin-$K" > "$d/console.log" 2>&1
echo "EXIT=$? $G-$K" >> "$d/console.log"
