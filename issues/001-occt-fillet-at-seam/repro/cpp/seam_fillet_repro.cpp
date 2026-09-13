// seam_fillet_repro.cpp
//
// Reproduction, in plain OCCT with no FreeCAD layer, of the fillet defect measured on
// FreeCAD 1.1.1 / OCCT 7.8.1.
//
// Fixture (the owner's minimal pair, mirrored from common/python/seamlib.py::build_fixture):
// a 25 x 25.7184 x 10 box with a cylindrical pocket whose axis is tilted 45 degrees about Y
// and crosses the top-front corner line of the box at (25, 12.7, 10). The pocket is radius
// 6.647656 and 13 mm deep. The edge under test is the straight top-front corner edge at
// x = 25, z = 10 running away from the pocket -- length 6.370744 mm.
//
// The cylinder is rotated about its OWN axis before the cut. A solid of revolution rotated
// about its own axis is the same region of space (the Python pair proves this: each version
// cuts the other to 0.000000000000), so the ONLY thing that changes is where the seam -- the
// u = 0 iso-line of the cylindrical face -- lands relative to the filleted edge's end vertex.
//
// Measured in FreeCAD on this fixture (repro/python/03_minimal_pair.py):
//   seam 11.514078 mm from the edge -> valid, removed +1.3681 mm3 (analytic +1.3672), BOP clean
//   seam  0.000000 mm from the edge -> isValid() False, volume 5849.4736 -> 6205.9267,
//                                      i.e. the volume GROWS by 356.4531 mm3, BOP dirty
//
// Build and run: see repro/cpp/README.md

#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRep_Tool.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Shape.hxx>
#include <TopoDS_Vertex.hxx>
#include <Geom_Curve.hxx>
#include <Geom_Line.hxx>
#include <Geom_Surface.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <gp_Ax1.hxx>
#include <gp_Ax2.hxx>
#include <gp_Dir.hxx>
#include <gp_Pnt.hxx>
#include <gp_Trsf.hxx>
#include <gp_Vec.hxx>
#include <Standard_Failure.hxx>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {

// --- the box -------------------------------------------------------------
const Standard_Real BX = 25.0, BY = 25.7184, BZ = 10.0;

// --- the tilted pocket ---------------------------------------------------
const Standard_Real POCKET_R   = 6.647656;
const Standard_Real POCKET_LEN = 13.0;
const Standard_Real STANDOFF   = 6.0;     // sketch plane offset along the axis

gp_Dir PocketDir() { return gp_Dir(1.0, 0.0, 1.0); }   // gp_Dir normalises
gp_Pnt AxisPoint() { return gp_Pnt(BX, 12.7, BZ); }    // axis crosses the corner line

// Fixture with the pocket cylinder pre-rotated by angleDeg about its own axis.
// The rotation leaves the solid identical and moves only the seam.
TopoDS_Shape MakeFixture(Standard_Real angleDeg)
{
  TopoDS_Shape box = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), BX, BY, BZ).Shape();

  const gp_Dir dir = PocketDir();
  const gp_Pnt planePt = AxisPoint().Translated(gp_Vec(dir) * STANDOFF);

  // The pocket is cut from the sketch plane back into the material, i.e. along -dir.
  gp_Ax2 axis(planePt, gp_Dir(-dir.X(), -dir.Y(), -dir.Z()));
  TopoDS_Shape cyl = BRepPrimAPI_MakeCylinder(axis, POCKET_R, POCKET_LEN).Shape();

  if (angleDeg != 0.0) {
    gp_Trsf t;
    t.SetRotation(gp_Ax1(planePt, dir), angleDeg * M_PI / 180.0);
    cyl = BRepBuilderAPI_Transform(cyl, t, Standard_True).Shape();
  }

  return BRepAlgoAPI_Cut(box, cyl).Shape();
}

Standard_Real Volume(const TopoDS_Shape& s)
{
  GProp_GProps props;
  BRepGProp::VolumeProperties(s, props);
  return props.Mass();
}

// The straight top-front corner edge at x = BX, z = BZ whose far end has y > 15.
Standard_Boolean TargetEdge(const TopoDS_Shape& s, TopoDS_Edge& out)
{
  TopTools_IndexedMapOfShape edges;
  TopExp::MapShapes(s, TopAbs_EDGE, edges);
  Standard_Boolean found = Standard_False;

  for (Standard_Integer i = 1; i <= edges.Extent(); ++i) {
    TopoDS_Edge e = TopoDS::Edge(edges(i));
    Standard_Real f, l;
    Handle(Geom_Curve) c = BRep_Tool::Curve(e, f, l);
    if (c.IsNull() || Handle(Geom_Line)::DownCast(c).IsNull()) continue;

    TopoDS_Vertex v1, v2;
    TopExp::Vertices(e, v1, v2);
    if (v1.IsNull() || v2.IsNull()) continue;
    gp_Pnt p1 = BRep_Tool::Pnt(v1), p2 = BRep_Tool::Pnt(v2);

    if (std::fabs(p1.X() - BX) > 1e-6 || std::fabs(p2.X() - BX) > 1e-6) continue;
    if (std::fabs(p1.Z() - BZ) > 1e-6 || std::fabs(p2.Z() - BZ) > 1e-6) continue;
    if (std::max(p1.Y(), p2.Y()) <= 15.0) continue;

    out = e;
    found = Standard_True;   // keep the last match, as the Python fixture does
  }
  return found;
}

// Seam edges: an edge that is closed on its face carries TWO pcurves on that one face.
std::vector<TopoDS_Edge> SeamEdges(const TopoDS_Shape& s)
{
  std::vector<TopoDS_Edge> out;
  for (TopExp_Explorer fx(s, TopAbs_FACE); fx.More(); fx.Next()) {
    TopoDS_Face f = TopoDS::Face(fx.Current());
    for (TopExp_Explorer ex(f, TopAbs_EDGE); ex.More(); ex.Next()) {
      TopoDS_Edge e = TopoDS::Edge(ex.Current());
      if (BRep_Tool::IsClosed(e, f)) out.push_back(e);
    }
  }
  return out;
}

// Smallest distance from the filleted edge to any seam edge.
Standard_Real DistToSeam(const TopoDS_Edge& target, const std::vector<TopoDS_Edge>& seams)
{
  Standard_Real best = -1.0;
  for (std::size_t i = 0; i < seams.size(); ++i) {
    BRepExtrema_DistShapeShape d(target, seams[i]);
    if (!d.IsDone()) continue;
    if (best < 0.0 || d.Value() < best) best = d.Value();
  }
  return best;
}

// (1 - pi/4) * r^2 * L : volume removed by a fillet on a straight edge between two
// perpendicular planes.
Standard_Real AnalyticRemoved(Standard_Real r, Standard_Real length)
{
  return (1.0 - M_PI / 4.0) * r * r * length;
}

}  // namespace

int main(int argc, char** argv)
{
  const Standard_Real radius = (argc > 1) ? std::atof(argv[1]) : 1.0;

  const Standard_Real angleList[] = {
      0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 105.0, 135.0, 180.0, 270.0};
  const std::vector<Standard_Real> angles(
      angleList, angleList + sizeof(angleList) / sizeof(angleList[0]));

  std::printf("OCCT seam/fillet repro (owner's minimal pair) -- fillet radius %.3f\n\n", radius);
  std::printf("%-9s %-12s %-9s %-7s %-13s %-13s %-11s %s\n",
              "rotDeg", "distSeam", "IsDone", "Valid", "volume", "removed", "analytic", "BOPcheck");

  for (std::size_t k = 0; k < angles.size(); ++k) {
    const Standard_Real a = angles[k];
    TopoDS_Shape base = MakeFixture(a);
    Standard_Real v0 = Volume(base);

    TopoDS_Edge edge;
    if (!TargetEdge(base, edge)) { std::printf("%-9.3f  <target edge not found>\n", a); continue; }

    std::vector<TopoDS_Edge> seams = SeamEdges(base);
    Standard_Real dist = seams.empty() ? -1.0 : DistToSeam(edge, seams);

    GProp_GProps lp;
    BRepGProp::LinearProperties(edge, lp);
    Standard_Real expect = AnalyticRemoved(radius, lp.Mass());

    try {
      BRepFilletAPI_MakeFillet mk(base);
      mk.Add(radius, edge);
      mk.Build();

      if (!mk.IsDone()) {
        std::printf("%-9.3f %-12.6f %-9s %-7s %-13s %-13s %-11.4f %s\n",
                    a, dist, "NOT DONE", "-", "-", "-", expect, "-");
        continue;
      }

      TopoDS_Shape res = mk.Shape();
      Standard_Boolean ok = BRepCheck_Analyzer(res).IsValid();
      Standard_Real v1 = Volume(res);

      BRepAlgoAPI_Check bop(res);

      std::printf("%-9.3f %-12.6f %-9s %-7s %-13.4f %+-13.4f %-11.4f %s\n",
                  a, dist, "done", ok ? "yes" : "NO", v1, v0 - v1, expect,
                  bop.IsValid() ? "clean" : "DIRTY");
    } catch (const Standard_Failure& e) {
      std::printf("%-9.3f %-12.6f RAISED %s: %s\n",
                  a, dist, e.DynamicType()->Name(), e.GetMessageString());
    }
  }

  std::printf("\n'removed' is volume(base) - volume(filleted): a NEGATIVE value means the\n"
              "fillet ADDED material, which no fillet can legitimately do.\n");
  return 0;
}
