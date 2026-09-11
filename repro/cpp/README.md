# C++ reproduction: OCCT fillet corrupted by a seam at the spine's end vertex

Direct `BRepFilletAPI_MakeFillet` reproduction, no FreeCAD Python layer.
Measured against OCCT 7.8.1 as shipped in FreeCAD 1.1 (`TKernel.dll` reports
`FileVersion 7.8.1`), on Windows 10 x64.

Analysis and full measurements: `docs/OCCT_SOURCES.md`.

## What it shows

The owner's minimal pair, rebuilt in plain OCCT: a 25 x 25.7184 x 10 box with a
cylindrical pocket (R = 6.647656, depth 13) whose axis is tilted 45 degrees about
Y and crosses the top-front corner line at (25, 12.7, 10). The fillet (r = 1.0)
goes on the straight corner edge at x = 25, z = 10, length 6.370744 mm.

The cylinder is rotated about its **own axis** before the cut, so the solid is
identical at every angle while the cylindrical face's seam moves. Only the seam
position changes, yet:

```
rotDeg    distSeam     IsDone    Valid   volume        removed       analytic    BOPcheck
0.000     11.514078    done      yes     5848.1055     +1.3681       1.3672      clean
15.000    12.348638    done      yes     5848.1055     +1.3681       1.3672      clean
45.000    13.151970    done      yes     5848.1055     +1.3681       1.3672      clean
90.000    13.295312    done      yes     5848.1055     +1.3681       1.3672      clean
180.000   11.514078    done      yes     5848.1055     +1.3681       1.3672      clean
270.000   0.000000     done      NO      6224.4449     -374.9713     1.3672      DIRTY
```

While the seam stays clear of the edge the fillet removes +1.3681 mm3 against an
analytic +1.3672. The moment the seam touches the edge, `Build()` still reports
success and returns a solid that is invalid, BOP-dirty, and whose **volume has
grown by 374.97 mm3** — a fillet that adds material.

Cross-check against the same fixture driven through FreeCAD
(`repro/python/03_minimal_pair.py`): distance 11.514077943 mm and +1.3681 mm3 in
the good case — identical to the last digit printed. In the broken case FreeCAD
measures a growth of 356.4531 mm3 versus 374.9713 here; the difference is only
which seam phase lands exactly on the edge, because FreeCAD counts `AngleXU` from
the sketch's X axis and this program from the `gp_Ax2` `XDirection`.

A **chamfer** of the same size on the same edge is unharmed in both cases
(measured in the Python script), so the defect is specific to the fillet path.

## Build (measured working on this machine)

Prerequisites, all already present:

| | |
|---|---|
| MSVC | `C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.36.32532` |
| Windows SDK | `C:/Program Files (x86)/Windows Kits/10`, version `10.0.22000.0` |
| OCCT DLLs | `C:/Program Files/FreeCAD 1.1/bin` (no headers, no `.lib` files) |
| OCCT headers | from the 7.8.1 clone, flattened into `build/occt-inc` |
| Import libs | generated from the DLLs into `build/implib` |

The FreeCAD distribution ships neither OCCT headers nor import libraries, so both
are produced first. Steps 1 and 2 only need running once.

### 1. Flatten the headers out of the OCCT clone

```bash
INC=C:/dev/seamless/build/occt-inc
mkdir -p "$INC"
cd C:/dev/seamless/occt/src
find . \( -name '*.hxx' -o -name '*.lxx' -o -name '*.gxx' \) -exec cp -n {} "$INC"/ \;
```

8358 files, 49 MB.

### 2. Generate import libraries from the shipped DLLs

`dumpbin /exports` + `lib /def`. Both tools ship with Visual Studio 2022.
Note the `-EXPORTS` dash form and `MSYS2_ARG_CONV_EXCL` — in Git Bash a leading
`/` is rewritten into a Windows path and the call fails.

```bash
MSVC="C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64"
BIN="C:/Program Files/FreeCAD 1.1/bin"
OUT=C:/dev/seamless/build/implib; mkdir -p "$OUT"; cd "$OUT"
export MSYS2_ARG_CONV_EXCL='*'

for m in TKernel TKMath TKG2d TKG3d TKGeomBase TKBRep TKGeomAlgo \
         TKTopAlgo TKPrim TKBO TKBool TKFillet TKShHealing TKService; do
  "$MSVC/dumpbin.exe" -EXPORTS "$BIN/$m.dll" > "$m.exports.txt"
  { echo "LIBRARY $m"; echo "EXPORTS";
    awk 'f && NF>=4 && $1 ~ /^[0-9]+$/ {print "  " $4} /ordinal *hint *RVA *name/ {f=1}' "$m.exports.txt";
  } > "$m.def"
  "$MSVC/lib.exe" -def:"$m.def" -machine:x64 -name:"$m.dll" -out:"$m.lib"
done
```

Measured: 14 of 14 succeeded, 0 failures, 1709 symbols for TKernel through 1218
for TKService. The exports are MSVC-mangled C++ names, so the DLLs were built
with MSVC and link normally.

### 3. Compile and run

`build.sh` sets the MSVC and SDK paths itself, so **no `vcvars` and no `cmd.exe`**
are needed (the owner's machine must stay headless).

```bash
bash repro/cpp/build.sh
PATH="/c/Program Files/FreeCAD 1.1/bin:$PATH" build/seam_fillet_repro.exe 2.0
```

The argument is the fillet radius (default 2.0). The DLLs are not on the default
PATH, so the FreeCAD `bin` directory must be prepended when running.

## Caution

A fillet near a seam can hang — 9.2 minutes with no completion was measured on
the owner's real part. Always run under a deadline:

```bash
timeout 600 build/seam_fillet_repro.exe 2.0
```

On this fixture all 17 configurations returned within 0.05 s, so the hang is not
reproduced here.
