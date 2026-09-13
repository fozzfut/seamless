#!/usr/bin/env bash
# run_seam_fillet.sh -- drive repro/cpp/seam_fillet.cpp over the case matrix.
#
# ONE PROCESS PER CASE, EACH WITH ITS OWN DEADLINE. A fillet near a seam can fail to
# return at all (9.2 minutes with no completion was measured on the owner's real part),
# so a case must never be able to stall the run. `timeout` kills it and exit code 124 is
# recorded as HANG -- which is a measurement, not an error.
#
# The program writes unbuffered, so the log of a killed case still holds every line it
# had reached before the deadline.
#
# Usage:  bash repro/cpp/run_seam_fillet.sh [deadline_seconds]

set -u

EXE="${EXE:-C:/dev/freecad-kernel-fixes/build/seam-fillet/seam_fillet.exe}"
OCCT_BIN="${OCCT_BIN:-C:/dev/freecad-kernel-fixes/build/occt-release/win64/vc14/bin}"
LOGDIR="${LOGDIR:-C:/dev/freecad-kernel-fixes/build/seam-fillet/logs}"
DEADLINE="${1:-600}"

# The freshly built kernel and nothing else. FreeCAD's bin is deliberately NOT added:
# if these DLLs were missing the program would fail to start rather than silently pick
# up FreeCAD's copy of OCCT.
#
# PATH entries must be POSIX-style here. Git Bash does NOT translate a "C:/..." entry
# inside PATH, so the loader never sees the directory and every case dies with exit 127
# ("DLL not found") -- which looks exactly like a real failure. Convert explicitly.
OCCT_BIN_POSIX=$(printf '%s' "$OCCT_BIN" | sed -E 's#^([A-Za-z]):#/\l\1#')
export PATH="$OCCT_BIN_POSIX:$PATH"

if [ ! -f "$EXE" ]; then
  echo "ERROR: $EXE not found -- run build-scripts/build-seam-fillet.ps1 first" >&2
  exit 2
fi
if [ ! -d "$OCCT_BIN_POSIX" ]; then
  echo "ERROR: OCCT bin $OCCT_BIN_POSIX not found" >&2
  exit 2
fi

mkdir -p "$LOGDIR"

# The minimal pair, located by `--probe`:
#   rot 0   -> seam endpoint 11.514078 mm from the spine's end vertex  (good)
#   rot 270 -> seam endpoint  0.000000 mm from it, i.e. exactly on it  (bad)
ROTS="${ROTS:-0 270}"
RADII="${RADII:-0.25 0.5 1.0 2.0}"

printf '%-8s %-8s %-12s %-22s %-7s %-14s %-14s %-12s %-8s %s\n' \
  rotDeg radius distVtx status valid volume removed analytic secs bop

for rot in $ROTS; do
  for r in $RADII; do
    log="$LOGDIR/case_rot${rot}_r${r}.log"
    start=$(date +%s.%N)
    timeout -k 5 "$DEADLINE" "$EXE" --case --rot "$rot" --radius "$r" > "$log" 2>&1
    rc=$?
    end=$(date +%s.%N)
    wall=$(awk -v a="$start" -v b="$end" 'BEGIN{printf "%.3f", b-a}')

    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
      # Killed by its own deadline: the case did not return. Record it and move on.
      printf '%-8s %-8s %-12s %-22s %-7s %-14s %-14s %-12s %-8s %s\n' \
        "$rot" "$r" "-" "HANG_${DEADLINE}s" "-" "-" "-" "-" "$wall" "-"
      continue
    fi
    if [ "$rc" -ne 0 ]; then
      printf '%-8s %-8s %-12s %-22s %-7s %-14s %-14s %-12s %-8s %s\n' \
        "$rot" "$r" "-" "EXIT_$rc" "-" "-" "-" "-" "$wall" "-"
      continue
    fi

    # The program prints exactly one RESULT line; parse its key=value pairs.
    line=$(grep '^RESULT ' "$log" | tail -1)
    if [ -z "$line" ]; then
      printf '%-8s %-8s %-12s %-22s %-7s %-14s %-14s %-12s %-8s %s\n' \
        "$rot" "$r" "-" "NO_RESULT_LINE" "-" "-" "-" "-" "$wall" "-"
      continue
    fi
    get() { echo "$line" | tr ' ' '\n' | grep "^$1=" | cut -d= -f2-; }
    printf '%-8s %-8s %-12s %-22s %-7s %-14s %-14s %-12s %-8s %s\n' \
      "$rot" "$r" "$(get dist)" "$(get status)" "$(get valid)" "$(get vol)" \
      "$(get removed)" "$(get analytic)" "$(get secs)" "$(get bop)"
  done
done

echo
echo "per-case logs: $LOGDIR"
echo "deadline was ${DEADLINE} s per case; 'removed' is volume(base) - volume(filleted),"
echo "so a NEGATIVE value means the fillet ADDED material, which no fillet can do."
