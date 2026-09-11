#!/usr/bin/env bash
# deploy_kernels.sh -- fill build/bin-<variant> from the private build tree.
#
# Every kernel directory gets the SAME 18 modeling DLLs, freshly built in this session from
# C:/dev/occt-cond, plus the DRAWEXE/Tcl files that are not affected by the patch.  Only
# TKFillet.dll differs between the directories, and it is copied by the caller right after
# building the variant it belongs to -- so the kernel under test is the one variable.
set -eu
TREE=/c/dev/seamless/build/occt-cond/win64/vc14/bin
for v in stock cond blunt; do
  d=/c/dev/seamless/build/bin-$v
  [ -d "$d" ] || { echo "missing $d" >&2; exit 2; }
  for f in "$TREE"/*.dll; do
    b=$(basename "$f")
    [ "$b" = "TKFillet.dll" ] && continue      # the variable, copied per variant
    cp -f "$f" "$d/$b"
  done
  echo "$v: $(ls "$d"/*.dll | wc -l) dlls"
done
