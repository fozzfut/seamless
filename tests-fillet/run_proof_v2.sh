#!/usr/bin/env bash
# run_proof_v2.sh <group> <outroot> -- the proof run for the narrowed guard.
#
# Runs ONE OCCT test group TWICE against each kernel, so that "stock and patched
# differ" can be separated from "two runs of anything differ".  The kernels are
# three directories that differ in TKFillet.dll and in nothing else:
#     build/bin-stock  pristine V7_8_1
#     build/bin-cond   the narrowed guard (patches/0002)
#     build/bin-blunt  the guard simply dropped (patches/0001) -- the positive
#                      control: it MUST show the H4/D6 regression, otherwise a
#                      clean stock-vs-cond diff would only prove the harness blind.
#
# Every run gets its own output directory and its own deadline; a group that does
# not return is killed and that is recorded, not silently retried.
set -u
GROUP="${1:?usage: run_proof_v2.sh <group> <outroot>}"
ROOT="${2:?}"
DEADLINE="${DEADLINE:-1800}"
KERNELS="${KERNELS:-stock cond blunt}"
REPEATS="${REPEATS:-2}"
HERE="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$ROOT"
for k in $KERNELS; do
  n=$REPEATS
  [ "$k" = "blunt" ] && n=1          # control only needs to fire once
  i=1
  while [ "$i" -le "$n" ]; do
    out="$ROOT/$k$i"
    rm -rf "$out"; mkdir -p "$out"
    echo "=== $GROUP : kernel $k run $i -> $out"
    start=$(date +%s.%N)
    timeout -k 30 "$DEADLINE" bash "$HERE/run_group_cond.sh" "$GROUP" "$out" \
        "/c/dev/seamless/build/bin-$k" > "$ROOT/$k$i.console" 2>&1
    rc=$?
    end=$(date +%s.%N)
    awk -v a="$start" -v b="$end" -v r="$rc" -v k="$k$i" \
        'BEGIN{printf "RUN %-8s exit=%d wall=%.1f s\n", k, r, b-a}'
    grep -E '^TKFillet|^kernel' "$ROOT/$k$i.console" | sed 's/^/    /'
    i=$((i+1))
  done
done
