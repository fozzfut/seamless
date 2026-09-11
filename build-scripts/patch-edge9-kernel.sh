#!/usr/bin/env bash
# patch-edge9-kernel.sh -- apply / revert patches/0001-chfi3d-recale-unconditional.patch in the
# PRIVATE source tree C:/dev/occt-e9, by exact anchor rather than by line number.
#
# WHY NOT `git apply`: C:/dev/occt-e9 is not a git repository -- it is a `git archive V7_8_1`
# extraction, deliberately outside the shared clone, because another agent team edits
# C:/dev/seamless/occt/src/ChFi3d while this measurement runs.
#
# The anchor is asserted UNIQUE before anything is written. A patch that silently applied in
# the wrong place, or twice, would poison every number measured afterwards.
#
# Usage:  bash build-scripts/patch-edge9-kernel.sh apply|revert|status

set -eu

SRC="${OCCT_E9_SRC:-C:/dev/occt-e9}"
FILE="$SRC/src/ChFi3d/ChFi3d_Builder_C1.cxx"
PRISTINE="C:/dev/seamless/build/occt-src-orig/ChFi3d_Builder_C1.cxx"

GUARDED='    if (onsame) ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));'
PATCHED='    ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));'

[ -f "$FILE" ] || { echo "ERROR: $FILE not found" >&2; exit 2; }

count() { grep -cF "$1" "$FILE" || true; }

case "${1:-status}" in
  status)
    echo "file     : $FILE"
    echo "md5      : $(md5sum "$FILE" | cut -d' ' -f1)"
    echo "pristine : $(md5sum "$PRISTINE" | cut -d' ' -f1)  (build/occt-src-orig, == tag V7_8_1)"
    echo "guarded call  'if (onsame) ChFi3d_Recale(...)' : $(count "$GUARDED")"
    echo "unguarded call 'ChFi3d_Recale(...)' at col 5   : $(count "$PATCHED")"
    ;;
  apply)
    n=$(count "$GUARDED")
    [ "$n" = "1" ] || { echo "ERROR: guarded call appears $n times, expected exactly 1" >&2; exit 3; }
    # sed with a fixed string: the line contains no regex metacharacters except the
    # parentheses and dots, so it is escaped explicitly instead of being trusted.
    python - "$FILE" <<'PY'
import sys
path = sys.argv[1]
guarded = "    if (onsame) ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));"
patched = "    ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));"
with open(path, "r", newline="") as f:
    text = f.read()
assert text.count(guarded) == 1, "anchor is not unique"
with open(path, "w", newline="") as f:
    f.write(text.replace(guarded, patched))
print("applied: one line changed")
PY
    diff "$PRISTINE" "$FILE" || true
    ;;
  revert)
    cp "$PRISTINE" "$FILE"
    echo "reverted from $PRISTINE"
    md5sum "$PRISTINE" "$FILE"
    ;;
  *)
    echo "usage: $0 apply|revert|status" >&2; exit 2;;
esac
