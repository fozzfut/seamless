// kernel_smoke.cpp
//
// Proof that the OCCT kernel built locally from C:/dev/freecad-kernel-fixes/occt (tag V7_8_1)
// is usable from a plain C++ program: headers resolve, import libraries link,
// DLLs load, and the modelling algorithms produce correct numbers.
//
// Scenario (all dimensions in mm, analytic volumes known in advance):
//   1. box       40 x 30 x 20                       -> 24000
//   2. cylinder  r = 6, h = 20, axis Z at (12,15,0) -> pi*36*20 = 2261.946711
//   3. cut       box - cylinder                     -> 21738.053289
//   4. fillet    r = 3 on the vertical box edge at (x=0, y=0)
//                removes (r^2 - pi*r^2/4)*h = (9 - 2.25*pi)*20 = 38.628330
//                                                   -> 21699.424959
//
// Validity is reported two ways on purpose, because they disagree in the
// defect this project is about:
//   BRepCheck_Analyzer  - the topological/geometric checker (what FreeCAD's
//                         Shape.isValid() calls)
//   BRepAlgoAPI_Check   - the BOP-level checker (small edges + self-interference)

#include <Standard_Version.hxx>

#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepTools.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Shape.hxx>
#include <gp_Ax2.hxx>
#include <gp_Dir.hxx>
#include <gp_Pnt.hxx>

#include <cmath>
#include <cstdio>

// Adaptive Gauss integration, so the printed volume can be compared with the
// analytic value at a meaningful tolerance instead of an arbitrary one.
// The overload returns the relative error actually reached.
static double Volume(const TopoDS_Shape& theShape, double* theRelErr = 0)
{
  GProp_GProps aProps;
  const double anErr = BRepGProp::VolumeProperties(theShape, aProps, 1.0e-11);
  if (theRelErr != 0)
  {
    *theRelErr = anErr;
  }
  return aProps.Mass();
}

static int CountSub(const TopoDS_Shape& theShape, const TopAbs_ShapeEnum theType)
{
  TopTools_IndexedMapOfShape aMap;
  TopExp::MapShapes(theShape, theType, aMap);
  return aMap.Extent();
}

static void Report(const char* theName, const TopoDS_Shape& theShape,
                   const double theExpected)
{
  double aRelErr = 0.0;
  const double aVol = Volume(theShape, &aRelErr);

  BRepCheck_Analyzer anAnalyzer(theShape);
  const bool isAnalyzerValid = anAnalyzer.IsValid() == Standard_True;

  BRepAlgoAPI_Check aBopCheck(theShape);
  const bool isBopValid = aBopCheck.IsValid() == Standard_True;

  printf("%-22s volume = %14.6f   expected = %14.6f   delta = %+.3e   (integration rel.err %.1e)\n",
         theName, aVol, theExpected, aVol - theExpected, aRelErr);
  printf("%-22s faces = %3d  edges = %3d  vertices = %3d\n",
         "", CountSub(theShape, TopAbs_FACE), CountSub(theShape, TopAbs_EDGE),
         CountSub(theShape, TopAbs_VERTEX));
  printf("%-22s BRepCheck_Analyzer.IsValid = %s   BRepAlgoAPI_Check.IsValid = %s\n\n",
         "", isAnalyzerValid ? "true" : "false", isBopValid ? "true" : "false");
}

// Pick the vertical (Z-parallel) straight edge of the box whose midpoint sits
// on the (x=0, y=0) corner. Deterministic: exactly one edge satisfies this.
static bool FindCornerEdge(const TopoDS_Shape& theShape, TopoDS_Edge& theEdge)
{
  for (TopExp_Explorer anExp(theShape, TopAbs_EDGE); anExp.More(); anExp.Next())
  {
    const TopoDS_Edge& anEdge = TopoDS::Edge(anExp.Current());
    BRepAdaptor_Curve aCurve(anEdge);
    if (aCurve.GetType() != GeomAbs_Line)
    {
      continue;
    }
    const double aMid = 0.5 * (aCurve.FirstParameter() + aCurve.LastParameter());
    const gp_Pnt aP = aCurve.Value(aMid);
    const gp_Dir aD = aCurve.Line().Direction();
    if (std::abs(std::abs(aD.Z()) - 1.0) < 1.0e-7
     && aP.X() < 1.0e-7 && aP.Y() < 1.0e-7)
    {
      theEdge = anEdge;
      return true;
    }
  }
  return false;
}

int main(int argc, char** argv)
{
  printf("OCCT linked into this binary: OCC_VERSION_COMPLETE = %s\n",
         OCC_VERSION_COMPLETE);
  printf("built from C:/dev/freecad-kernel-fixes/occt, linked against "
         "C:/dev/freecad-kernel-fixes/build/occt-release/win64/vc14/lib\n\n");

  const double PI = 3.14159265358979323846;

  // 1. box
  const TopoDS_Shape aBox = BRepPrimAPI_MakeBox(40.0, 30.0, 20.0).Shape();
  Report("box 40x30x20", aBox, 40.0 * 30.0 * 20.0);

  // 2. cylinder
  const gp_Ax2 anAxis(gp_Pnt(12.0, 15.0, 0.0), gp_Dir(0.0, 0.0, 1.0));
  const TopoDS_Shape aCyl = BRepPrimAPI_MakeCylinder(anAxis, 6.0, 20.0).Shape();
  Report("cylinder r6 h20", aCyl, PI * 36.0 * 20.0);

  // 3. cut
  BRepAlgoAPI_Cut aCutter(aBox, aCyl);
  if (!aCutter.IsDone())
  {
    printf("FAIL: BRepAlgoAPI_Cut did not finish\n");
    return 2;
  }
  const TopoDS_Shape aCut = aCutter.Shape();
  const double aCutExpected = 40.0 * 30.0 * 20.0 - PI * 36.0 * 20.0;
  Report("box - cylinder", aCut, aCutExpected);

  // 4. fillet an ordinary edge (a plain convex box corner, far from the hole)
  TopoDS_Edge anEdge;
  if (!FindCornerEdge(aCut, anEdge))
  {
    printf("FAIL: corner edge not found\n");
    return 3;
  }
  BRepFilletAPI_MakeFillet aFillet(aCut);
  aFillet.Add(3.0, anEdge);
  aFillet.Build();
  if (!aFillet.IsDone())
  {
    printf("FAIL: BRepFilletAPI_MakeFillet did not finish\n");
    return 4;
  }
  const TopoDS_Shape aFilleted = aFillet.Shape();
  const double aRemoved = (9.0 - 2.25 * PI) * 20.0;
  Report("fillet r3 on 1 edge", aFilleted, aCutExpected - aRemoved);

  printf("fillet removed %.6f mm3 (analytic %.6f mm3)\n",
         Volume(aCut) - Volume(aFilleted), aRemoved);

  if (argc > 1)
  {
    if (BRepTools::Write(aFilleted, argv[1]))
    {
      printf("wrote result shape to %s\n", argv[1]);
    }
  }

  const double anExpected = aCutExpected - aRemoved;
  const double anErr = std::abs(Volume(aFilleted) - anExpected) / anExpected;
  const bool isOk = anErr < 1.0e-9;
  printf("\nRESULT: %s (relative volume error %.3e, tolerance 1e-9)\n",
         isOk ? "PASS" : "FAIL", anErr);
  return isOk ? 0 : 1;
}
