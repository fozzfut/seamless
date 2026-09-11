#!/usr/bin/env bash
# run_edge9_proof.sh <outroot> -- the owner's part, seven radii, three kernels, twice each.
#
# One process per radius with its own deadline (a radius that does not return is killed and
# recorded as TIMEOUT: that is the stock behaviour at r=0.5 and r=0.55 and it is a result).
# Each kernel is run twice into separate log directories so that "stock differs from patched"
# can be told apart from "two runs differ"; the RESULT lines of the two repeats are then
# compared verbatim.
set -u
ROOT="${1:?usage: run_edge9_proof.sh <outroot>}"
DEADLINE="${DEADLINE:-310}"
KERNELS="${KERNELS:-stock cond blunt}"
REPEATS="${REPEATS:-2}"
EXE="${EXE:-C:/dev/seamless/build/edge9-cond/edge9_fillet.exe}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT"
for k in $KERNELS; do
  i=1
  while [ "$i" -le "$REPEATS" ]; do
    echo "############ kernel=$k run=$i"
    LOGDIR="$ROOT/$k$i" EXE="$EXE" \
      bash "$HERE/run_edge9.sh" "C:/dev/seamless/build/bin-$k" "$k$i" "$DEADLINE" \
      2>&1 | tee "$ROOT/$k$i.table"
    i=$((i+1))
  done
done
echo
echo "############ REPEATABILITY: RESULT lines of run 1 vs run 2, same kernel"
for k in $KERNELS; do
  [ -d "$ROOT/${k}1" ] && [ -d "$ROOT/${k}2" ] || continue
  # secs= is wall time of the fillet call and is the one field that legitimately
  # differs between two runs of the same binary; everything else -- validity,
  # volume, delta, BOP state -- must repeat digit for digit.
  a=$(cat "$ROOT/${k}1"/r*.log 2>/dev/null | grep '^RESULT ' | sed 's/ secs=[0-9.]*//' | sort)
  b=$(cat "$ROOT/${k}2"/r*.log 2>/dev/null | grep '^RESULT ' | sed 's/ secs=[0-9.]*//' | sort)
  if [ "$a" = "$b" ]; then
    echo "$k: run1 == run2  ($(echo "$a" | grep -c RESULT) RESULT lines identical)"
  else
    echo "$k: RUN1 != RUN2"
    diff <(echo "$a") <(echo "$b") | sed 's/^/    /'
  fi
done
