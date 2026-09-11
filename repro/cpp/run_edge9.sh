#!/usr/bin/env bash
# run_edge9.sh -- the radius sweep on the owner's real part, against ONE kernel.
#
# ONE PROCESS PER RADIUS, EACH WITH ITS OWN DEADLINE. Radii 0.5 and 0.55 did not return in
# FreeCAD after 9 minutes (docs/MEASUREMENTS.md 5.4), so a radius must never be able to stall
# the sweep. `timeout` kills it, exit code 124 is recorded as TIMEOUT, and that is a result:
# "the kernel did not return" is exactly what has to be measured and compared.
#
# The kernel under test is chosen by the DIRECTORY OF DLLS put on PATH, and by nothing else:
# the executable is built once and never rebuilt between the two runs, so the only thing that
# differs between a stock sweep and a patched sweep is TKFillet.dll.
#
# Usage:
#   bash repro/cpp/run_edge9.sh <kernel-bin-dir> <label> [deadline_seconds]
#
# Example:
#   bash repro/cpp/run_edge9.sh C:/dev/seamless/build/kernel-e9-stock stock 300
#   bash repro/cpp/run_edge9.sh C:/dev/seamless/build/kernel-e9-fix   patched 300

set -u

EXE="${EXE:-C:/dev/seamless/build/edge9/edge9_fillet.exe}"
BREP="${BREP:-C:/path/to/temp/claude/c--Program-Files-FreeCAD-1-1/90e2ee8a-0198-4b2f-ae54-0503653173cc/scratchpad/edge9/body_tip.brep}"
KERNEL="${1:?usage: run_edge9.sh <kernel-bin-dir> <label> [deadline]}"
LABEL="${2:?usage: run_edge9.sh <kernel-bin-dir> <label> [deadline]}"
DEADLINE="${3:-300}"
LOGDIR="${LOGDIR:-C:/dev/seamless/build/edge9/logs-$LABEL}"
RADII="${RADII:-0.1 0.25 0.45 0.5 0.55 1.0 2.0}"

# PATH entries must be POSIX-style here. Git Bash does NOT translate a "C:/..." entry inside
# PATH, so the loader would never see the directory and every case would die with exit 127
# ("DLL not found") -- which looks exactly like a real failure. Convert explicitly.
posix() { printf '%s' "$1" | sed -E 's#^([A-Za-z]):#/\l\1#'; }
KERNEL_POSIX=$(posix "$KERNEL")

if [ ! -f "$EXE" ]; then echo "ERROR: $EXE not found -- run build-scripts/build-edge9.ps1" >&2; exit 2; fi
if [ ! -f "$BREP" ]; then echo "ERROR: $BREP not found -- run repro/python/13_export_user_part.py" >&2; exit 2; fi
if [ ! -f "$KERNEL/TKFillet.dll" ]; then echo "ERROR: no TKFillet.dll in $KERNEL" >&2; exit 2; fi

export PATH="$KERNEL_POSIX:$PATH"
mkdir -p "$LOGDIR"

echo "kernel   = $KERNEL"
echo "TKFillet = $(md5sum "$KERNEL/TKFillet.dll" | cut -d' ' -f1)"
echo "exe      = $EXE"
echo "deadline = ${DEADLINE} s per radius"
echo
printf '%-8s %-9s %-24s %-8s %-14s %-14s %-10s %s\n' \
  radius status isValid volume delta wall bop label

for r in $RADII; do
  log="$LOGDIR/r${r}.log"
  start=$(date +%s.%N)
  timeout -k 10 "$DEADLINE" "$EXE" --brep "$BREP" --radius "$r" > "$log" 2>&1
  rc=$?
  end=$(date +%s.%N)
  wall=$(awk -v a="$start" -v b="$end" 'BEGIN{printf "%.3f", b-a}')

  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    printf '%-8s %-9s %-24s %-8s %-14s %-14s %-10s %s\n' \
      "$r" "TIMEOUT" "-" "-" "-" "${wall}s" "-" "$LABEL"
    continue
  fi
  if [ "$rc" -ne 0 ]; then
    printf '%-8s %-9s %-24s %-8s %-14s %-14s %-10s %s\n' \
      "$r" "EXIT_$rc" "-" "-" "-" "${wall}s" "-" "$LABEL"
    continue
  fi

  line=$(grep '^RESULT ' "$log" | tail -1)
  if [ -z "$line" ]; then
    printf '%-8s %-9s %-24s %-8s %-14s %-14s %-10s %s\n' \
      "$r" "NO_RESULT" "-" "-" "-" "${wall}s" "-" "$LABEL"
    continue
  fi
  get() { echo "$line" | tr ' ' '\n' | grep "^$1=" | cut -d= -f2-; }
  printf '%-8s %-9s %-24s %-8s %-14s %-14s %-10s %s\n' \
    "$r" "$(get status)" "$(get valid)" "$(get vol)" "$(get delta)" "${wall}s" "$(get bop)" "$LABEL"
done

echo
echo "per-radius logs: $LOGDIR"
echo "delta is volume(result) - volume(base); a POSITIVE delta means the fillet ADDED"
echo "material, which no fillet can do."
