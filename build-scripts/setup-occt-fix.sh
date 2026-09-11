#!/usr/bin/env bash
# setup-occt-fix.sh -- build the isolated source tree and build tree used for the
# seam-fillet fix, from nothing, with deadlines on every step.
#
# WHY AN ISOLATED TREE AT ALL
# ---------------------------
# The shared clone C:/dev/seamless/occt is written by more than one agent team. During
# this work a second writer changed ChFi3d_Builder_C1.cxx between a patch and its build,
# and rebuilt TKFillet.dll underneath a running measurement. Numbers produced that way
# cannot be attributed to anybody's change. Everything here therefore happens in
# C:/dev/occt-fix (sources) and C:/dev/seamless/build/occt-fix (build tree), and the
# runtime is assembled explicitly rather than inherited from PATH.
#
# WHAT IT DOES
#   1. copies CMakeLists.txt + adm + src + the top-level files out of the shared clone
#   2. resets the two ChFi3d files from build/occt-src-orig, which is verified byte-equal
#      to `git show V7_8_1:` -- so the starting point is pristine 7.8.1 whatever state the
#      shared clone happens to be in
#   3. configures the build tree with exactly the options of build/occt-release
#   4. builds all 18 toolkits and installs a SELF-CONTAINED kernel (real headers)
#
# Usage:  bash build-scripts/setup-occt-fix.sh [--fast]
#           --fast : build only TKFillet, seeding the other 17 import libraries from
#                    build/occt-release. 24 s instead of ~7 min; enough to measure a
#                    change to ChFi3d, not enough to ship a kernel.

set -eu

SHARED="${SHARED_OCCT:-C:/dev/seamless/occt}"
SRC="${OCCT_FIX_SRC:-C:/dev/occt-fix}"
BLD="${OCCT_FIX_BUILD:-C:/dev/seamless/build/occt-fix}"
INST="${OCCT_FIX_INSTALL:-C:/dev/seamless/install/occt-fix}"
ORIG="C:/dev/seamless/build/occt-src-orig"
RELEASE="C:/dev/seamless/build/occt-release"
CMAKE="${CMAKE:-C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe}"

FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

say() { printf '\n=== %s ===\n' "$1"; }

[ -d "$SHARED/src" ] || { echo "ERROR: $SHARED/src not found" >&2; exit 2; }
[ -f "$ORIG/ChFi3d_Builder_C1.cxx" ] || { echo "ERROR: pristine copies missing in $ORIG" >&2; exit 2; }
[ -x "$CMAKE" ] || { echo "ERROR: cmake not at $CMAKE" >&2; exit 2; }

say "disk before"
df -m /c | tail -1

say "1. copying sources -> $SRC"
mkdir -p "$SRC"
timeout -k 60 1800 cp -r "$SHARED/CMakeLists.txt" "$SHARED/adm" "$SHARED/src" "$SRC/"
# the install step needs the licence files that sit at the top level
for f in LICENSE_LGPL_21.txt OCCT_LGPL_EXCEPTION.txt README.txt; do
  [ -f "$SHARED/$f" ] && cp "$SHARED/$f" "$SRC/"
done
du -sm "$SRC"

say "2. resetting the two ChFi3d files to verified-pristine 7.8.1"
cp "$ORIG/ChFi3d_Builder.cxx"    "$SRC/src/ChFi3d/ChFi3d_Builder.cxx"
cp "$ORIG/ChFi3d_Builder_C1.cxx" "$SRC/src/ChFi3d/ChFi3d_Builder_C1.cxx"
md5sum "$SRC/src/ChFi3d/ChFi3d_Builder_C1.cxx" "$ORIG/ChFi3d_Builder_C1.cxx"

say "3. configuring $BLD"
mkdir -p "$BLD"
timeout -k 60 1800 "$CMAKE" -S "$SRC" -B "$BLD" \
  -G "Visual Studio 17 2022" -A x64 \
  -DBUILD_MODULE_FoundationClasses=ON \
  -DBUILD_MODULE_ModelingData=ON \
  -DBUILD_MODULE_ModelingAlgorithms=ON \
  -DBUILD_MODULE_Visualization=OFF \
  -DBUILD_MODULE_ApplicationFramework=OFF \
  -DBUILD_MODULE_DataExchange=OFF \
  -DBUILD_MODULE_Draw=OFF \
  -DBUILD_MODULE_DETools=OFF \
  -DBUILD_DOC_Overview=OFF \
  -DBUILD_LIBRARY_TYPE=Shared \
  -DBUILD_CPP_STANDARD=C++17 \
  -DBUILD_RELEASE_DISABLE_EXCEPTIONS=ON \
  -DBUILD_USE_PCH=OFF \
  -DBUILD_RESOURCES=OFF \
  -DUSE_TBB=OFF -DUSE_D3D=OFF -DUSE_TCL=OFF \
  -DINSTALL_DIR="$INST"

if [ "$FAST" = "1" ]; then
  say "4. FAST: seeding the 17 sibling import libraries and building TKFillet only"
  mkdir -p "$BLD/win64/vc14/lib"
  for l in "$RELEASE"/win64/vc14/lib/*.lib; do
    n=$(basename "$l"); [ "$n" = "TKFillet.lib" ] && continue
    cp "$l" "$BLD/win64/vc14/lib/$n"
  done
  # -p:BuildProjectReferences=false stops MSBuild rebuilding the other 17 toolkits;
  # their .lib files are import stubs from identical pristine sources and the same
  # compiler, so linking against them is sound.
  time timeout -k 60 1800 "$CMAKE" --build "$BLD" --target TKFillet --config Release \
       -- -m -v:m -p:BuildProjectReferences=false
  echo "NOTE: only TKFillet was built. For a shippable kernel run without --fast."
else
  say "4. building all 18 toolkits (expect about 7 minutes on 12 cores)"
  timeout -k 120 5400 "$CMAKE" --build "$BLD" --config Release -- -m -v:m
  say "5. installing a self-contained kernel -> $INST"
  timeout -k 60 1800 "$CMAKE" --install "$BLD" --config Release > /dev/null
  echo "headers: $(ls "$INST/inc" | wc -l)   dlls: $(ls "$INST"/win64/vc14/bin/*.dll | wc -l)   libs: $(ls "$INST"/win64/vc14/lib/*.lib | wc -l)"
  head -1 "$INST/inc/ChFi3d_Builder.hxx"
  echo "(a real header, not a one-line forwarder into a source tree)"
fi

say "disk after"
df -m /c | tail -1
echo
echo "next:  python build-scripts/chfi3d_patch.py fix      # apply the fix"
echo "       python build-scripts/chfi3d_patch.py trace    # or the instrumentation"
echo "       then rebuild TKFillet and re-run repro/cpp/run_seam_fillet.sh"
