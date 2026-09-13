// fillet_regress.cpp
//
// A regression battery for the one-line change to ChFi3d_Builder_C1.cxx described in
// docs/FIX.md: making ChFi3d_Recale unconditional in PerformOneCorner.
//
// WHY THIS PROGRAM EXISTS
// -----------------------
// OCCT ships a large test suite, but it is driven by DRAWEXE, which needs the Draw
// module, which needs Tcl/Tk. Neither is built here and neither can be (docs/BUILD.md,
// section 2: Draw is OFF because Tcl/Tk is not on the machine). So "run OCCT's own
// tests" is not available, and saying so is more useful than pretending otherwise.
// This is the substitute: a battery of fillets, chamfers and booleans on shapes that do
// and do not carry seams, printing one deterministic line per case.
//
// HOW IT IS USED
//   fillet_regress > before.txt   # with the pristine kernel on PATH
//   fillet_regress > after.txt    # with the patched kernel on PATH
//   diff before.txt after.txt
//
// The claim the fix has to survive is: every line that is not a seam-corner case is
// BYTE-IDENTICAL between the two runs. That is a far stronger statement than "the
// numbers look similar", and a diff is not something one can talk one's way around.
//
// WHY THE BLAST RADIUS SHOULD BE NARROW (and this battery tries to falsify it)
// ChFi3d_Recale changes a point only when the surface is periodic AND the two points are
// more than half a period apart in u or v. Every case on a plane, a non-periodic spline,
// or a cylinder whose two corner points are close, must therefore be untouched. The
// battery deliberately includes cylinders, cones, through holes, blind holes, fused and
// cut solids, multi-edge fillets and fillets whose corners meet -- plus a family of
// small-hole/large-fillet cases built specifically to look for a corner curve that
// legitimately spans more than half a cylinder, which is the one situation where this
// change could plausibly pick the wrong arc.

#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeCone.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepPrimAPI_MakeTorus.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepFilletAPI_MakeChamfer.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Shape.hxx>
#include <BRep_Tool.hxx>
#include <gp_Ax2.hxx>
#include <gp_Pnt.hxx>
#include <gp_Dir.hxx>
#include <OSD.hxx>
#include <Standard_Failure.hxx>
#include <Standard_Version.hxx>

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

double Volume(const TopoDS_Shape& s)
{
  GProp_GProps p;
  BRepGProp::VolumeProperties(s, p);
  return p.Mass();
}

void Counts(const TopoDS_Shape& s, int& nf, int& ne)
{
  TopTools_IndexedMapOfShape m;
  TopExp::MapShapes(s, TopAbs_FACE, m); nf = m.Extent();
  m.Clear();
  TopExp::MapShapes(s, TopAbs_EDGE, m); ne = m.Extent();
}

// BRepAlgoAPI_Check is what FreeCAD's Shape.check(True) calls; BRepCheck_Analyzer is
// what Shape.isValid() calls. The seam defect is precisely a case where the second says
// true and the first says otherwise, so both are printed for every case.
const char* Bop(const TopoDS_Shape& s)
{
  try {
    BRepAlgoAPI_Check c(s, Standard_True, Standard_True);
    return c.IsValid() ? "clean" : "DIRTY";
  } catch (Standard_Failure&) {
    return "RAISED";
  }
}

// Every case prints exactly one line, in a fixed format, so two runs can be diffed.
void Report(const std::string& name, bool done, const TopoDS_Shape& res)
{
  if (!done || res.IsNull()) {
    std::printf("%-34s NOTDONE\n", name.c_str());
    return;
  }
  int nf = 0, ne = 0;
  Counts(res, nf, ne);
  const bool valid = BRepCheck_Analyzer(res).IsValid() == Standard_True;
  std::printf("%-34s done valid=%-5s vol=%18.9f faces=%3d edges=%3d bop=%s\n",
              name.c_str(), valid ? "true" : "FALSE", Volume(res), nf, ne, Bop(res));
}

// Fillet the edges whose index (1-based, TopExp map order) is listed. Index order is
// deterministic for a given construction, which is all a regression diff needs.
void FilletByIndex(const std::string& name, const TopoDS_Shape& base,
                   const std::vector<int>& idx, double r)
{
  try {
    TopTools_IndexedMapOfShape em;
    TopExp::MapShapes(base, TopAbs_EDGE, em);
    BRepFilletAPI_MakeFillet mk(base);
    int added = 0;
    for (size_t i = 0; i < idx.size(); ++i) {
      if (idx[i] < 1 || idx[i] > em.Extent()) continue;
      const TopoDS_Edge& e = TopoDS::Edge(em(idx[i]));
      if (BRep_Tool::Degenerated(e)) continue;
      mk.Add(r, e);
      ++added;
    }
    if (!added) { std::printf("%-34s NO_EDGE\n", name.c_str()); return; }
    mk.Build();
    Report(name, mk.IsDone() == Standard_True, mk.IsDone() ? mk.Shape() : TopoDS_Shape());
  } catch (Standard_Failure& f) {
    std::printf("%-34s RAISED %s\n", name.c_str(), f.GetMessageString());
  }
}

void FilletAll(const std::string& name, const TopoDS_Shape& base, double r)
{
  try {
    BRepFilletAPI_MakeFillet mk(base);
    int added = 0;
    for (TopExp_Explorer ex(base, TopAbs_EDGE); ex.More(); ex.Next()) {
      const TopoDS_Edge& e = TopoDS::Edge(ex.Current());
      if (BRep_Tool::Degenerated(e)) continue;
      mk.Add(r, e);
      ++added;
    }
    if (!added) { std::printf("%-34s NO_EDGE\n", name.c_str()); return; }
    mk.Build();
    Report(name, mk.IsDone() == Standard_True, mk.IsDone() ? mk.Shape() : TopoDS_Shape());
  } catch (Standard_Failure& f) {
    std::printf("%-34s RAISED %s\n", name.c_str(), f.GetMessageString());
  }
}

void ChamferByIndex(const std::string& name, const TopoDS_Shape& base,
                    const std::vector<int>& idx, double d)
{
  try {
    TopTools_IndexedMapOfShape em;
    TopExp::MapShapes(base, TopAbs_EDGE, em);
    BRepFilletAPI_MakeChamfer mk(base);
    int added = 0;
    for (size_t i = 0; i < idx.size(); ++i) {
      if (idx[i] < 1 || idx[i] > em.Extent()) continue;
      const TopoDS_Edge& e = TopoDS::Edge(em(idx[i]));
      if (BRep_Tool::Degenerated(e)) continue;
      mk.Add(d, e);
      ++added;
    }
    if (!added) { std::printf("%-34s NO_EDGE\n", name.c_str()); return; }
    mk.Build();
    Report(name, mk.IsDone() == Standard_True, mk.IsDone() ? mk.Shape() : TopoDS_Shape());
  } catch (Standard_Failure& f) {
    std::printf("%-34s RAISED %s\n", name.c_str(), f.GetMessageString());
  }
}

void Boolean(const std::string& name, const TopoDS_Shape& a, const TopoDS_Shape& b,
             int op)
{
  try {
    TopoDS_Shape r;
    if      (op == 0) r = BRepAlgoAPI_Cut(a, b).Shape();
    else if (op == 1) r = BRepAlgoAPI_Fuse(a, b).Shape();
    else              r = BRepAlgoAPI_Common(a, b).Shape();
    Report(name, true, r);
  } catch (Standard_Failure& f) {
    std::printf("%-34s RAISED %s\n", name.c_str(), f.GetMessageString());
  }
}

TopoDS_Shape Box(double x, double y, double z)
{ return BRepPrimAPI_MakeBox(x, y, z).Shape(); }

TopoDS_Shape BoxAt(double px, double py, double pz, double x, double y, double z)
{ return BRepPrimAPI_MakeBox(gp_Pnt(px, py, pz), x, y, z).Shape(); }

TopoDS_Shape Cyl(double px, double py, double pz, double r, double h)
{ return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(px, py, pz), gp_Dir(0, 0, 1)), r, h).Shape(); }

}  // namespace

int main()
{
  OSD::SetSignal(Standard_False);
  std::setvbuf(stdout, NULL, _IONBF, 0);
  std::printf("fillet_regress on OCCT %s\n", OCC_VERSION_COMPLETE);
  std::printf("----------------------------------------------------------------------\n");

  // ---- 1. plain boxes: no periodic face anywhere, must be untouched ----
  const TopoDS_Shape b1 = Box(10, 20, 30);
  FilletByIndex("box/one-edge r=1",   b1, {1}, 1.0);
  FilletByIndex("box/one-edge r=3",   b1, {1}, 3.0);
  FilletByIndex("box/two-edges r=2",  b1, {1, 2}, 2.0);
  FilletByIndex("box/three-at-corner",b1, {1, 3, 5}, 1.5);
  FilletAll    ("box/all-edges r=1",  b1, 1.0);
  FilletAll    ("box/all-edges r=2",  b1, 2.0);
  ChamferByIndex("box/chamfer one",   b1, {1}, 1.0);
  ChamferByIndex("box/chamfer all-ish", b1, {1, 2, 3, 4}, 0.8);

  // ---- 2. primitives that DO carry a seam ----
  const TopoDS_Shape c1 = Cyl(0, 0, 0, 5, 10);
  FilletAll    ("cylinder/all-edges r=1", c1, 1.0);
  FilletByIndex("cylinder/one-rim r=2",   c1, {1}, 2.0);
  FilletByIndex("cylinder/one-rim r=0.5", c1, {1}, 0.5);
  const TopoDS_Shape cone = BRepPrimAPI_MakeCone(4.0, 2.0, 8.0).Shape();
  FilletAll    ("cone/all-edges r=0.5",   cone, 0.5);
  FilletAll    ("cone/all-edges r=1",     cone, 1.0);

  // ---- 3. booleans, then fillets on their result: the seam-carrying cases ----
  const TopoDS_Shape thru  = BRepAlgoAPI_Cut(Box(20, 20, 10), Cyl(10, 10, -1, 4, 12)).Shape();
  Report("cut/through-hole (base)", true, thru);
  FilletByIndex("thruhole/rim r=0.5",  thru, {1}, 0.5);
  FilletByIndex("thruhole/rim r=1",    thru, {1}, 1.0);
  FilletAll    ("thruhole/all r=0.5",  thru, 0.5);

  const TopoDS_Shape blind = BRepAlgoAPI_Cut(Box(20, 20, 10), Cyl(10, 10, 4, 4, 12)).Shape();
  Report("cut/blind-hole (base)", true, blind);
  FilletAll    ("blindhole/all r=0.5", blind, 0.5);
  FilletByIndex("blindhole/rim r=1",   blind, {1, 2}, 1.0);

  const TopoDS_Shape fused = BRepAlgoAPI_Fuse(Box(20, 20, 10), BoxAt(5, 5, 10, 10, 10, 10)).Shape();
  Report("fuse/step (base)", true, fused);
  FilletAll("fused/all r=1", fused, 1.0);
  FilletAll("fused/all r=2", fused, 2.0);

  const TopoDS_Shape boss = BRepAlgoAPI_Fuse(Box(20, 20, 10), Cyl(10, 10, 10, 4, 8)).Shape();
  Report("fuse/cylindrical-boss (base)", true, boss);
  FilletAll    ("boss/all r=0.5", boss, 0.5);
  FilletByIndex("boss/foot r=1",  boss, {1, 2, 3}, 1.0);

  // ---- 4. a slot across a hole: fillet corners land ON a cylindrical face ----
  // This is the shape family the seam defect lives in: the pocket rim is cut into arcs
  // with real end vertices, and a fillet spine ends on the cylindrical face.
  const TopoDS_Shape slotted =
    BRepAlgoAPI_Cut(thru, BoxAt(-1, 9.4, 8.8, 22, 1.2, 3)).Shape();
  Report("cut/slot-across-hole (base)", true, slotted);
  FilletAll    ("slotted/all r=0.3", slotted, 0.3);
  FilletByIndex("slotted/few r=0.5", slotted, {1, 2, 3, 4}, 0.5);
  FilletByIndex("slotted/few r=1",   slotted, {1, 2, 3, 4}, 1.0);

  // ---- 5. small hole + large fillet: hunting for a corner curve that LEGITIMATELY
  // spans more than half a cylinder, the one case where the fix could pick wrongly ----
  for (int k = 0; k < 4; ++k) {
    const double hr[4] = {0.6, 1.0, 1.5, 2.5};
    const double fr[4] = {2.0, 2.0, 3.0, 4.0};
    char nm[64];
    const TopoDS_Shape sh =
      BRepAlgoAPI_Cut(Box(20, 20, 10), Cyl(10, 10, -1, hr[k], 12)).Shape();
    std::snprintf(nm, sizeof(nm), "smallhole r=%.1f fillet r=%.1f", hr[k], fr[k]);
    FilletAll(nm, sh, fr[k]);
  }

  // ---- 6. plain booleans, to show the change cannot reach them ----
  Boolean("bool/cut box-cyl",    Box(20, 20, 10), Cyl(10, 10, -1, 4, 12), 0);
  Boolean("bool/fuse box-cyl",   Box(20, 20, 10), Cyl(10, 10, 5, 4, 12), 1);
  Boolean("bool/common box-cyl", Box(20, 20, 10), Cyl(10, 10, -1, 4, 12), 2);
  Boolean("bool/cut box-box",    Box(20, 20, 10), BoxAt(5, 5, 5, 10, 10, 10), 0);
  Boolean("bool/common sph-box", BRepPrimAPI_MakeSphere(6.0).Shape(), Box(5, 5, 5), 2);
  Boolean("bool/cut torus-box",
          BRepPrimAPI_MakeTorus(8.0, 2.0).Shape(), BoxAt(-10, -10, -1, 20, 20, 2), 0);

  std::printf("----------------------------------------------------------------------\n");
  std::printf("end\n");
  return 0;
}
