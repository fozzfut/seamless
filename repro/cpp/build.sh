#!/usr/bin/env bash
# Build the OCCT seam/fillet repro against the FreeCAD 1.1 OCCT 7.8.1 DLLs.
# No vcvars / cmd.exe: the MSVC and Windows SDK paths are set explicitly.
set -u
export MSYS2_ARG_CONV_EXCL='*'

MSVC_VER=14.36.32532
SDK_VER=10.0.22000.0
VS="C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/$MSVC_VER"
SDK="C:/Program Files (x86)/Windows Kits/10"
OCCT_INC="${OCCT_INC:-C:/dev/seamless/build/occt-inc}"
IMPLIB="${IMPLIB:-C:/dev/seamless/build/implib}"
OUTDIR="${OUTDIR:-C:/dev/seamless/build}"

export INCLUDE="$VS/include;$SDK/Include/$SDK_VER/ucrt;$SDK/Include/$SDK_VER/um;$SDK/Include/$SDK_VER/shared"
export LIB="$VS/lib/x64;$SDK/Lib/$SDK_VER/ucrt/x64;$SDK/Lib/$SDK_VER/um/x64"
export PATH="$VS/bin/Hostx64/x64:$PATH"

LIBS="TKernel.lib TKMath.lib TKG2d.lib TKG3d.lib TKGeomBase.lib TKBRep.lib TKGeomAlgo.lib TKTopAlgo.lib TKPrim.lib TKBO.lib TKBool.lib TKFillet.lib TKShHealing.lib"

mkdir -p "$OUTDIR"
"$VS/bin/Hostx64/x64/cl.exe" /nologo /std:c++17 /EHsc /MD /O2 /D_USE_MATH_DEFINES \
  /I"$OCCT_INC" \
  "C:/dev/seamless/repro/cpp/seam_fillet_repro.cpp" \
  /Fo"$OUTDIR/" /Fe"$OUTDIR/seam_fillet_repro.exe" \
  /link /LIBPATH:"$IMPLIB" $LIBS
