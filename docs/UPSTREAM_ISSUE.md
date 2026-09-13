# Draft: issue for Open-Cascade-SAS/OCCT

Ready to paste as a GitHub issue. The pull request that follows it goes against the `IR` branch,
after the CLA is approved (`.github/CONTRIBUTING.md`: fork, branch from `IR`, clang-format, DRAW
and GTest locally, Draft PR, title `Group - Summary`). What is still missing before a PR is listed
at the end of this file.

---

**Title:** Modeling Algorithms - Fillet ending at a vertex where a periodic face's seam ends gives an invalid solid or does not return

### Description

`BRepFilletAPI_MakeFillet` on a straight edge whose end vertex coincides with the seam of a closed
periodic face (here a cylindrical pocket wall) produces a wrong result. Depending on the radius the
result is invalid, or valid by `BRepCheck_Analyzer` but with the wrong volume, or the call does not
return. The same edge on the same solid fillets correctly when the seam is moved away from the
vertex, so the geometry is not the problem.

Environment: OCCT 7.8.1 (tag `V7_8_1`), Windows x64, MSVC 19.36. The code involved is unchanged at
`V7_9_0`, `V8_0_1` and `master`.

### Minimal reproduction

A box 25 x 25.7184 x 10 with a cylindrical pocket R 6.647656, axis tilted 45 degrees about Y,
crossing the corner line x = 25, z = 10. The pocket profile circle is built with its parameter
origin at AngleXU = 0 (seam 11.514078 mm from the corner edge) or AngleXU = 90 degrees (seam ending
exactly on the corner edge's end vertex). Rotating a full circle about its own axis moves no
material: the two solids cut each other to 0.000000000000 mm3 in both directions. Fillet r = 1.0
on the corner edge:

| seam position | isValid | BOPAlgo check | volume removed | analytic |
|---|---|---|---|---|
| 11.514078 mm away | true | clean | 1.368076 | 1.367173 |
| on the end vertex | false | Bad orientation of sub-shape | -374.970181 (volume grows) | 1.367173 |

A C++ reproduction (`BRepPrimAPI_MakeBox`, `BRepAlgoAPI_Cut`, `BRepFilletAPI_MakeFillet`,
`BRepCheck_Analyzer`, `GProp`) is available and will be attached; a DRAW test case is not written yet.

On a real part (same topology, from FreeCAD) the seam-on-vertex edge gives, per radius:

| r | stock | patched (below) |
|---|---|---|
| 0.10 | invalid, volume -142.297918 | valid, clean, removed 0.013672 (analytic 0.013671) |
| 0.25 | valid but BOP-dirty, removes 0.022222 instead of 0.085450 | valid, clean |
| 0.45 | invalid, removes 861.300134 | valid, clean |
| 0.50 | does not return (killed after 310 s) | valid, clean, 0.015 s |
| 0.55 | does not return (killed after 310 s) | valid, clean, 0.015 s |
| 1.00 | invalid, volume grows by 597.332276 | valid, clean, removed 1.368049 (analytic 1.367147) |
| 2.00 | invalid, volume grows by 578.014068 | valid, clean |

### Analysis

The corner is handled by `ChFi3d_Builder::PerformOneCorner`. At
`src/ChFi3d/ChFi3d_Builder_C1.cxx:807` (V7_8_1 numbering) the two 2d points on the face at the end
of the fillet are put on a common period branch only when `onsame` is true:

```cpp
if (onsame) ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));
```

On the seam case `onsame` is false, the points stay on different branches, and the u-window built
from them (`ChFi3d_Boite`, then `ChFi3d_BoundFac`) does not contain the corner vertex, so the
intersector works on the wrong part of the wall. `ChFi3d_ComputeCurves` validates its inputs by 3d
distance, where u and u + 2pi are the same point, so the branch error is not caught.

The sibling routine `ChFi3d_Builder::IntersectMoreCorner` already calls `ChFi3d_Recale`
unconditionally after the same setup (V7_8_1 line 4031; `V8_0_1` line 5054). In
`PerformIntersectionAtEnd` the equivalent reconciliation has been commented out since 2002:
`// commented by eap 30 May 2002 occ354 - the following code may cause trimming a wrong part of
periodic surface`.

Instrumented at line 807, three corners side by side:

| term | this report | blend/simple/H4 | blend/buildevol/D6 |
|---|---|---|---|
| onsame | 0 | 0 | 0 |
| face surface | CylindricalSurface | SurfaceOfRevolution | SurfaceOfRevolution |
| basis IsUPeriodic | 1 | 1 | 1 |
| face U range | [0, 6.283185307] | [0, 4.712388980] | [0, 4.712388980] |
| Bs.IsUClosed() | 1 | 0 | 0 |
| seam edges on the face | 2 (U) | 0 | 0 |
| pfac1.X / pfac2.X | 6.176614355 / 0.106570952 | 0.000000000 / 4.712388980 | 0.000000000 / 4.712388980 |
| ChFi3d_Recale would fire | 1 | 1 | 1 |
| it moves pfac2.X to | 6.389756260 | -1.570796327 | -1.570796327 |

`ChFi3d_Recale` tests periodicity of the basis surface, so on a face spanning three quarters of the
period it shifts a point a whole period outside the face. That is why simply dropping the guard is
wrong: it fixes this report and breaks blend/simple/H4 (Mass 426531 -> 426419,
BRepCheck_UnorientableShape + BRepCheck_NotClosed) and blend/buildevol/D6 (426060 -> 425937, same).

### Proposed change

```cpp
if (onsame || Bs.IsUClosed() || Bs.IsVClosed())
  ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));
```

`BRepAdaptor_Surface::IsUClosed` is "the surface is closed and the face's trim spans the whole
period", i.e. the face carries a seam. On the `!onsame` path `Bs` is initialised with
`Restriction = Standard_True` (line 748), which is what makes the term trim-aware; `onsame` stays
first because on its path `Bs` is loaded without restriction (lines 698-700).

### Evidence for the change

- The case in this report: all seven radii valid and BOPAlgo-clean, identical to the unguarded call.
- `blend`: 475 cases, 183 executed without external data; per-case logs byte-identical to stock
  (475 of 475); H4 and D6 back to stock values. The unguarded call, built in the same tree and run
  through the same harness, still shows both regressions.
- With the public dataset (`a-betenev/opencascade-dataset`): 2122 cases executed across `blend`,
  `chamfer`, `feat` and `offset`; 0 status changes; 21 of 3065 compared logs differ, and all 21
  differ between two runs of the same unpatched kernel as well (run-to-run noise in those cases).
- 943 cases still skip: their data files are not in the public dataset (confidential models and
  tracker attachments).

### Related

- PR #1507 "Modeling Algorithms - Fix fillets crossing periodic support seams" addresses a
  neighbouring symptom in `BRepBlend_Walking` / `ChFi3d_Builder_0.cxx` and does not touch
  `ChFi3d_Builder_C1.cxx`. It links FreeCAD issue 28544.
- The `occ354` note in `PerformIntersectionAtEnd` (see Analysis).

### Before a pull request

1. CLA signed and approved.
2. A DRAW test case under `tests/bugs/modalg_8` built from the fixture above, and a GTest in the
   style of `BRepFilletAPI_MakeFillet_Test.cxx`.
3. The change re-applied on `IR` (the file moved to `src/ModelingAlgorithms/TKFillet/ChFi3d/`)
   and the DRAW `blend`/`chamfer`/`feat` groups re-run there.
