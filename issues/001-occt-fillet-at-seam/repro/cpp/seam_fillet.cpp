// seam_fillet.cpp
//
// Reproduce the seam/fillet defect on BARE OCCT 7.8.1, with no FreeCAD anywhere in
// the picture: no FreeCAD DLLs, no Python, no PartDesign. The kernel this links
// against is the one built from source, out of tree, in
// C:/dev/freecad-kernel-fixes/build/occt-release (see docs/BUILD.md).
//
// WHY THIS PROGRAM EXISTS
// -----------------------
// The defect was first measured through FreeCAD 1.1.1 (repro/python/, docs/MEASUREMENTS.md).
// That leaves open the possibility that FreeCAD's own layer -- PartDesign::Fillet building
// its own arguments, FreeCAD shape healing, the TopoShape wrapper -- is what breaks the
// result. This program removes that possibility by calling BRepFilletAPI_MakeFillet directly.
//
// THE FIXTURE (mirrors common/python/seamlib.py, build_fixture)
// ------------------------------------------------------------
// A 25 x 25.7184 x 10 box with a cylindrical pocket, radius 6.647656, depth 13, whose axis
// is tilted 45 degrees about Y and crosses the top-front corner line of the box at
// (25, 12.7, 10). The edge under test is the straight top-front corner edge at x = 25,
// z = 10 that runs away from the pocket; it is 6.370744 mm long.
//
// HOW THE SEAM IS MOVED WITHOUT MOVING THE SOLID
// ----------------------------------------------
// A cylindrical face is periodic in u with period 2*pi, so it must carry a seam edge on its
// u = 0 iso-line. Where that iso-line sits is decided by the XDirection of the gp_Ax2 that
// defines the cylinder -- and by nothing else. So this program builds every version of the
// pocket from the same apex point, the same axis direction, the same radius and the same
// length, changing ONLY the XDirection, rotated by --rot degrees about the axis.
//
// That is a stronger construction than rotating a finished cylinder with a gp_Trsf: a
// transform produces a new solid whose numbers could differ in the last bits, whereas here
// the cylindrical surface is literally the same set of points, described with a different
// origin of the u parameter. The --identical mode measures this rather than asserting it.
//
// WHAT IS PRINTED
// ---------------
// For one case: BRepCheck_Analyzer validity (what FreeCAD Shape.isValid() calls), the
// GProp volume, the BOP check (BRepAlgoAPI_Check, what FreeCAD Shape.check(True) calls)
// with its fault types counted, and the wall time.
//
// HANGS ARE A RESULT, NOT A STALL
// -------------------------------
// Some radii near a seam do not return: 9.2 minutes with no completion was measured on the
// owner's real part. Therefore ONE case per process: the harness runs each (rotation, radius)
// pair as its own process under a deadline, and a killed process is recorded as HANG.
// stdout is unbuffered here on purpose, so every line a killed process reached survives.
//
// USAGE
//   seam_fillet --probe [--rot-from A --rot-to B --rot-step S]   fixture facts, no fillet
//   seam_fillet --identical <degA> <degB>                        prove the solids are the same
//   seam_fillet --case --rot <deg> --radius <r> [--brep <path>]  one fillet, one result line

#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
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
#include <Geom2d_Curve.hxx>
#include <gp_Ax1.hxx>
#include <gp_Ax2.hxx>
#include <gp_Dir.hxx>
#include <gp_Pnt.hxx>
#include <gp_Pnt2d.hxx>
#include <gp_Trsf.hxx>
#include <gp_Vec.hxx>
#include <BOPAlgo_CheckResult.hxx>
#include <BOPAlgo_ListOfCheckResult.hxx>
#include <OSD.hxx>
#include <Standard_Failure.hxx>
#include <Standard_Version.hxx>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <vector>

namespace {

// --------------------------------------------------------------------------
// the fixture constants, copied from common/python/seamlib.py
// --------------------------------------------------------------------------
const Standard_Real BX = 25.0, BY = 25.7184, BZ = 10.0;   // the box
const Standard_Real POCKET_R   = 6.647656;                // pocket radius
const Standard_Real POCKET_LEN = 13.0;                    // pocket depth
const Standard_Real STANDOFF   = 6.0;                     // sketch plane offset along the axis
const Standard_Real PI_ = 3.14159265358979323846;

// The pocket axis: tilted 45 degrees about Y. gp_Dir normalises for us.
gp_Dir PocketNormal() { return gp_Dir(1.0, 0.0, 1.0); }

// Where the pocket axis crosses the box top-front corner line.
gp_Pnt AxisPoint() { return gp_Pnt(BX, 12.7, BZ); }

// The cylinder apex: the sketch plane, STANDOFF out along the normal.
gp_Pnt ApexPoint()
{
  const gp_Dir n = PocketNormal();
  return AxisPoint().Translated(gp_Vec(n) * STANDOFF);
}

// The cutting direction: back into the material, i.e. minus the normal.
gp_Dir PocketAxisDir()
{
  const gp_Dir n = PocketNormal();
  return gp_Dir(-n.X(), -n.Y(), -n.Z());
}

// The reference XDirection at rot = 0. gp_Ax2 would otherwise pick one itself; naming it
// here makes the seam position an explicit, predictable function of rotDeg.
// The axis lies in the XZ plane, so Y is perpendicular to it and is a clean reference
// that does not depend on how gp_Ax2 would have guessed.
gp_Dir ReferenceX()
{
  return gp_Dir(gp_Vec(PocketAxisDir()) ^ gp_Vec(0.0, 1.0, 0.0));
}

// The gp_Ax2 of the pocket cylinder for a given seam rotation.
// Same location, same axis, same radius, same length at every rotation -- only the
// XDirection (the u = 0 reference of the cylindrical surface) turns.
gp_Ax2 PocketAxisFrame(Standard_Real rotDeg)
{
  const gp_Dir axis = PocketAxisDir();
  gp_Dir xdir = ReferenceX();
  if (rotDeg != 0.0) {
    gp_Trsf t;
    t.SetRotation(gp_Ax1(ApexPoint(), axis), rotDeg * PI_ / 180.0);
    xdir = gp_Dir(gp_Vec(xdir).Transformed(t));
  }
  return gp_Ax2(ApexPoint(), axis, xdir);
}

TopoDS_Shape MakeBoxShape()
{
  return BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), BX, BY, BZ).Shape();
}

TopoDS_Shape MakePocketCylinder(Standard_Real rotDeg)
{
  return BRepPrimAPI_MakeCylinder(PocketAxisFrame(rotDeg), POCKET_R, POCKET_LEN).Shape();
}

// The fixture: box minus the tilted pocket.
TopoDS_Shape MakeFixture(Standard_Real rotDeg)
{
  return BRepAlgoAPI_Cut(MakeBoxShape(), MakePocketCylinder(rotDeg)).Shape();
}

// --------------------------------------------------------------------------
// measurement helpers
// --------------------------------------------------------------------------

// Adaptive integration at the same tolerance the kernel smoke test used, so the volumes
// here are good to about 1e-11 mm3 and a 300 mm3 discrepancy cannot be an integration
// artefact.
Standard_Real Volume(const TopoDS_Shape& s)
{
  GProp_GProps p;
  BRepGProp::VolumeProperties(s, p, 1.0e-11);
  return p.Mass();
}

Standard_Real EdgeLength(const TopoDS_Shape& s)
{
  GProp_GProps p;
  BRepGProp::LinearProperties(s, p);
  return p.Mass();
}

// The straight top-front corner edge at x = BX, z = BZ, on the far side of the pocket.
Standard_Boolean TargetEdge(const TopoDS_Shape& s, TopoDS_Edge& out)
{
  TopTools_IndexedMapOfShape edges;
  TopExp::MapShapes(s, TopAbs_EDGE, edges);
  Standard_Boolean found = Standard_False;

  for (Standard_Integer i = 1; i <= edges.Extent(); ++i) {
    const TopoDS_Edge e = TopoDS::Edge(edges(i));
    Standard_Real f = 0.0, l = 0.0;
    Handle(Geom_Curve) c = BRep_Tool::Curve(e, f, l);
    if (c.IsNull() || Handle(Geom_Line)::DownCast(c).IsNull()) continue;

    TopoDS_Vertex v1, v2;
    TopExp::Vertices(e, v1, v2);
    if (v1.IsNull() || v2.IsNull()) continue;
    const gp_Pnt p1 = BRep_Tool::Pnt(v1), p2 = BRep_Tool::Pnt(v2);

    if (std::fabs(p1.X() - BX) > 1e-6 || std::fabs(p2.X() - BX) > 1e-6) continue;
    if (std::fabs(p1.Z() - BZ) > 1e-6 || std::fabs(p2.Z() - BZ) > 1e-6) continue;
    if (std::max(p1.Y(), p2.Y()) <= 15.0) continue;   // the half away from the pocket

    out = e;
    found = Standard_True;
  }
  return found;
}

// A seam edge is an edge that is CLOSED on its face: it carries two pcurves on that one
// face. BRep_Tool::IsClosed is exactly that test, and it is the C++ form of the fact
// measured through FreeCAD -- Line2d at u = 6.2832 and Line2d at u = 0.0000, same edge,
// same face.
struct SeamHit { TopoDS_Edge edge; TopoDS_Face face; };

std::vector<SeamHit> SeamEdges(const TopoDS_Shape& s)
{
  std::vector<SeamHit> out;
  for (TopExp_Explorer fx(s, TopAbs_FACE); fx.More(); fx.Next()) {
    const TopoDS_Face f = TopoDS::Face(fx.Current());
    for (TopExp_Explorer ex(f, TopAbs_EDGE); ex.More(); ex.Next()) {
      const TopoDS_Edge e = TopoDS::Edge(ex.Current());
      if (BRep_Tool::IsClosed(e, f)) { SeamHit h; h.edge = e; h.face = f; out.push_back(h); }
    }
  }
  return out;
}

// Distance from the edge we are about to fillet to the nearest seam curve.
Standard_Real DistToSeam(const TopoDS_Edge& target, const std::vector<SeamHit>& seams)
{
  Standard_Real best = -1.0;
  for (std::size_t i = 0; i < seams.size(); ++i) {
    BRepExtrema_DistShapeShape d(target, seams[i].edge);
    if (!d.IsDone()) continue;
    if (best < 0.0 || d.Value() < best) best = d.Value();
  }
  return best;
}

// The quantity the defect is actually about: how close a seam ENDPOINT comes to an
// ENDPOINT of the spine. The corner handling of the fillet is what breaks, so
// vertex-to-vertex is the distance that matters, not curve-to-curve.
Standard_Real DistSeamVertexToEdgeVertex(const TopoDS_Edge& target,
                                         const std::vector<SeamHit>& seams)
{
  TopoDS_Vertex a1, a2;
  TopExp::Vertices(target, a1, a2);
  if (a1.IsNull() || a2.IsNull()) return -1.0;
  const gp_Pnt ap[2] = { BRep_Tool::Pnt(a1), BRep_Tool::Pnt(a2) };

  Standard_Real best = -1.0;
  for (std::size_t i = 0; i < seams.size(); ++i) {
    TopoDS_Vertex b1, b2;
    TopExp::Vertices(seams[i].edge, b1, b2);
    if (b1.IsNull() || b2.IsNull()) continue;
    const gp_Pnt bp[2] = { BRep_Tool::Pnt(b1), BRep_Tool::Pnt(b2) };
    for (int k = 0; k < 2; ++k)
      for (int m = 0; m < 2; ++m) {
        const Standard_Real d = ap[k].Distance(bp[m]);
        if (best < 0.0 || d < best) best = d;
      }
  }
  return best;
}

// Volume a fillet of radius r must REMOVE from a straight edge of length L between two
// perpendicular planes: the corner left outside the quarter cylinder.
// Approximate at the far end of the spine, where the fillet meets the box corner; the
// measured good case agrees to 0.07 percent, which is why this is quoted as a sanity
// value, not as a tolerance to test against.
Standard_Real AnalyticRemoved(Standard_Real r, Standard_Real length)
{
  return (1.0 - PI_ / 4.0) * r * r * length;
}

const char* StatusName(BOPAlgo_CheckStatus s)
{
  switch (s) {
    case BOPAlgo_CheckUnknown:            return "CheckUnknown";
    case BOPAlgo_BadType:                 return "BadType";
    case BOPAlgo_SelfIntersect:           return "SelfIntersect";
    case BOPAlgo_TooSmallEdge:            return "TooSmallEdge";
    case BOPAlgo_NonRecoverableFace:      return "NonRecoverableFace";
    case BOPAlgo_IncompatibilityOfVertex: return "IncompatibilityOfVertex";
    case BOPAlgo_IncompatibilityOfEdge:   return "IncompatibilityOfEdge";
    case BOPAlgo_IncompatibilityOfFace:   return "IncompatibilityOfFace";
    case BOPAlgo_OperationAborted:        return "OperationAborted";
    case BOPAlgo_GeomAbs_C0:              return "GeomAbs_C0";
    case BOPAlgo_InvalidCurveOnSurface:   return "InvalidCurveOnSurface";
    case BOPAlgo_NotValid:                return "NotValid";
  }
  return "?";
}

// The BOP check, with its faults counted by type -- the C++ equivalent of FreeCAD
// Shape.check(True), which is the check that actually predicts whether later booleans work.
std::string BopVerdict(const TopoDS_Shape& s, Standard_Boolean& clean)
{
  try {
    BRepAlgoAPI_Check chk(s, Standard_True, Standard_True);
    clean = chk.IsValid();
    if (clean) return "clean";
    std::map<std::string, int> counts;
    const BOPAlgo_ListOfCheckResult& res = chk.Result();
    for (BOPAlgo_ListOfCheckResult::Iterator it(res); it.More(); it.Next())
      counts[StatusName(it.Value().GetCheckStatus())] += 1;
    std::string out = "DIRTY";
    for (std::map<std::string, int>::const_iterator it = counts.begin(); it != counts.end(); ++it) {
      char buf[128];
      std::snprintf(buf, sizeof(buf), " %s x%d", it->first.c_str(), it->second);
      out += buf;
    }
    return out;
  } catch (const Standard_Failure& e) {
    clean = Standard_False;
    return std::string("RAISED ") + e.DynamicType()->Name();
  }
}

int CountSub(const TopoDS_Shape& s, TopAbs_ShapeEnum t)
{
  TopTools_IndexedMapOfShape m;
  TopExp::MapShapes(s, t, m);
  return m.Extent();
}

double Now()
{
  using namespace std::chrono;
  return duration_cast<duration<double> >(steady_clock::now().time_since_epoch()).count();
}

// --------------------------------------------------------------------------
// modes
// --------------------------------------------------------------------------

// Fixture facts at one rotation, no fillet: is the solid the same, where is the seam,
// how far is it from the edge we mean to fillet.
int Probe(Standard_Real from, Standard_Real to, Standard_Real step)
{
  std::printf("OCCT %s -- fixture probe, NO fillet performed\n", OCC_VERSION_COMPLETE);
  std::printf("box %g x %g x %g, pocket R %g depth %g, axis 45 deg about Y through (%g, %g, %g)\n\n",
              BX, BY, BZ, POCKET_R, POCKET_LEN, AxisPoint().X(), AxisPoint().Y(), AxisPoint().Z());
  std::printf("%-8s %-15s %-6s %-6s %-6s %-12s %-12s %s\n",
              "rotDeg", "volume", "faces", "edges", "seams", "distCurve", "distVertex",
              "seam endpoint nearest the spine");

  for (Standard_Real a = from; a <= to + 1e-9; a += step) {
    const TopoDS_Shape sh = MakeFixture(a);
    TopoDS_Edge edge;
    if (!TargetEdge(sh, edge)) { std::printf("%-8.2f <target edge not found>\n", a); continue; }
    const std::vector<SeamHit> seams = SeamEdges(sh);

    // Report the seam endpoint that is nearest to the filleted edge.
    gp_Pnt nearest(0, 0, 0);
    Standard_Real best = -1.0;
    TopoDS_Vertex a1, a2; TopExp::Vertices(edge, a1, a2);
    for (std::size_t i = 0; i < seams.size(); ++i) {
      TopoDS_Vertex b1, b2; TopExp::Vertices(seams[i].edge, b1, b2);
      if (b1.IsNull() || b2.IsNull()) continue;
      const gp_Pnt bp[2] = { BRep_Tool::Pnt(b1), BRep_Tool::Pnt(b2) };
      for (int m = 0; m < 2; ++m) {
        const Standard_Real d = std::min(BRep_Tool::Pnt(a1).Distance(bp[m]),
                                         BRep_Tool::Pnt(a2).Distance(bp[m]));
        if (best < 0.0 || d < best) { best = d; nearest = bp[m]; }
      }
    }

    std::printf("%-8.2f %-15.6f %-6d %-6d %-6d %-12.6f %-12.6f (%.4f, %.4f, %.4f)\n",
                a, Volume(sh), CountSub(sh, TopAbs_FACE), CountSub(sh, TopAbs_EDGE),
                (int)seams.size(), DistToSeam(edge, seams),
                DistSeamVertexToEdgeVertex(edge, seams),
                nearest.X(), nearest.Y(), nearest.Z());
  }
  return 0;
}

// Prove the two versions are the same region of space, and that the seam moved.
int Identical(Standard_Real a, Standard_Real b)
{
  std::printf("OCCT %s -- are fixture(%.3f) and fixture(%.3f) the same solid?\n\n",
              OCC_VERSION_COMPLETE, a, b);

  const TopoDS_Shape A = MakeFixture(a), B = MakeFixture(b);
  const Standard_Real va = Volume(A), vb = Volume(B);
  std::printf("  volume(A) = %.9f\n  volume(B) = %.9f\n  difference = %.3e mm3\n\n",
              va, vb, va - vb);

  // Each cutting the other to nothing is the strong form: the same region, not merely
  // the same volume.
  const TopoDS_Shape AminusB = BRepAlgoAPI_Cut(A, B).Shape();
  const TopoDS_Shape BminusA = BRepAlgoAPI_Cut(B, A).Shape();
  const Standard_Real vab = Volume(AminusB), vba = Volume(BminusA);
  std::printf("  volume(A - B) = %.12f mm3\n  volume(B - A) = %.12f mm3\n", vab, vba);
  std::printf("  -> identical region of space: %s\n\n",
              (std::fabs(vab) < 1e-6 && std::fabs(vba) < 1e-6) ? "YES" : "NO");

  // The edge to be filleted must also be the same edge in both.
  TopoDS_Edge ea, eb;
  const Standard_Boolean gotA = TargetEdge(A, ea), gotB = TargetEdge(B, eb);
  if (gotA && gotB) {
    TopoDS_Vertex a1, a2, b1, b2;
    TopExp::Vertices(ea, a1, a2); TopExp::Vertices(eb, b1, b2);
    std::printf("  spine A: length %.9f  (%.4f, %.4f, %.4f) -> (%.4f, %.4f, %.4f)\n",
                EdgeLength(ea),
                BRep_Tool::Pnt(a1).X(), BRep_Tool::Pnt(a1).Y(), BRep_Tool::Pnt(a1).Z(),
                BRep_Tool::Pnt(a2).X(), BRep_Tool::Pnt(a2).Y(), BRep_Tool::Pnt(a2).Z());
    std::printf("  spine B: length %.9f  (%.4f, %.4f, %.4f) -> (%.4f, %.4f, %.4f)\n\n",
                EdgeLength(eb),
                BRep_Tool::Pnt(b1).X(), BRep_Tool::Pnt(b1).Y(), BRep_Tool::Pnt(b1).Z(),
                BRep_Tool::Pnt(b2).X(), BRep_Tool::Pnt(b2).Y(), BRep_Tool::Pnt(b2).Z());

    // And the seam must have moved -- otherwise there is no experiment.
    const Standard_Real da = DistSeamVertexToEdgeVertex(ea, SeamEdges(A));
    const Standard_Real db = DistSeamVertexToEdgeVertex(eb, SeamEdges(B));
    std::printf("  seam endpoint -> spine endpoint: A = %.9f mm, B = %.9f mm\n", da, db);
    std::printf("  -> the ONLY difference is the seam: %s\n",
                (std::fabs(da - db) > 1e-6) ? "YES" : "NO");
  } else {
    std::printf("  <target edge not found in %s>\n", gotA ? "B" : "A");
  }
  return 0;
}

// Dump the two pcurves a seam edge carries on its single face: the two-pcurve fact,
// measured on bare OCCT instead of through FreeCAD.
void DumpSeamPCurves(const TopoDS_Shape& s)
{
  const std::vector<SeamHit> seams = SeamEdges(s);
  for (std::size_t i = 0; i < seams.size(); ++i) {
    const TopoDS_Edge fwd = seams[i].edge;
    const TopoDS_Edge rev = TopoDS::Edge(fwd.Reversed());
    Standard_Real f = 0.0, l = 0.0;
    Handle(Geom2d_Curve) c1 = BRep_Tool::CurveOnSurface(fwd, seams[i].face, f, l);
    Handle(Geom2d_Curve) c2 = BRep_Tool::CurveOnSurface(rev, seams[i].face, f, l);
    if (c1.IsNull() || c2.IsNull()) continue;
    const gp_Pnt2d p1 = c1->Value(f), p2 = c2->Value(f);
    std::printf("    seam %d: pcurve A %s at u = %.4f ; pcurve B %s at u = %.4f"
                "  (one edge, two pcurves)\n",
                (int)i + 1, c1->DynamicType()->Name(), p1.X(),
                c2->DynamicType()->Name(), p2.X());
  }
}

// ONE case. This is what the harness runs in its own process, under its own deadline.
int Case(Standard_Real rotDeg, Standard_Real radius, const char* brepOut)
{
  std::printf("OCCT %s -- case rot = %.3f deg, fillet radius = %.3f\n",
              OCC_VERSION_COMPLETE, rotDeg, radius);

  const TopoDS_Shape base = MakeFixture(rotDeg);
  const Standard_Real v0 = Volume(base);

  TopoDS_Edge edge;
  if (!TargetEdge(base, edge)) {
    std::printf("RESULT rot=%.3f r=%.3f status=NO_TARGET_EDGE\n", rotDeg, radius);
    return 2;
  }

  const std::vector<SeamHit> seams = SeamEdges(base);
  const Standard_Real dCurve  = DistToSeam(edge, seams);
  const Standard_Real dVertex = DistSeamVertexToEdgeVertex(edge, seams);
  const Standard_Real len     = EdgeLength(edge);
  const Standard_Real expect  = AnalyticRemoved(radius, len);

  Standard_Boolean baseClean = Standard_False;
  const std::string baseBop = BopVerdict(base, baseClean);

  std::printf("  base solid: volume %.6f  faces %d  edges %d  seams %d  valid %s  BOP %s\n",
              v0, CountSub(base, TopAbs_FACE), CountSub(base, TopAbs_EDGE), (int)seams.size(),
              BRepCheck_Analyzer(base).IsValid() ? "true" : "FALSE", baseBop.c_str());
  DumpSeamPCurves(base);
  std::printf("  spine edge: length %.6f  dist(seam curve) %.6f"
              "  dist(seam vertex -> spine vertex) %.6f\n", len, dCurve, dVertex);
  std::printf("  analytic volume a correct fillet must REMOVE: %.6f mm3\n", expect);
  std::printf("  ... calling BRepFilletAPI_MakeFillet (a hang here is the measurement) ...\n");

  const double tf0 = Now();
  try {
    BRepFilletAPI_MakeFillet mk(base);
    mk.Add(radius, edge);
    mk.Build();
    const double tf = Now() - tf0;

    if (!mk.IsDone()) {
      std::printf("  Build() reported NOT DONE after %.3f s\n", tf);
      std::printf("RESULT rot=%.3f r=%.3f dist=%.6f status=NOTDONE valid=- vol=- removed=-"
                  " analytic=%.6f bop=- secs=%.3f\n", rotDeg, radius, dVertex, expect, tf);
      return 0;
    }

    const TopoDS_Shape res = mk.Shape();
    const Standard_Boolean valid = BRepCheck_Analyzer(res).IsValid();
    const Standard_Real v1 = Volume(res);
    Standard_Boolean clean = Standard_False;
    const std::string bop = BopVerdict(res, clean);
    const Standard_Real removed = v0 - v1;

    // The verdict. A fillet that removes the analytic amount and passes the BOP check is
    // correct; anything else is not. The two failure shapes are named apart because the
    // silent one -- valid = true, BOP dirty -- is the dangerous one.
    const char* verdict;
    if      (removed < 0.0)                              verdict = "BROKEN_VOLUME_GREW";
    else if (std::fabs(removed - expect) > 0.05 * expect) verdict = "BROKEN_WRONG_VOLUME";
    else if (!clean)                                     verdict = "BROKEN_BOP_DIRTY";
    else if (!valid)                                     verdict = "BROKEN_INVALID";
    else                                                 verdict = "OK";

    std::printf("  result: valid %s  volume %.6f  removed %+.6f mm3  BOP %s  fillet took %.3f s\n",
                valid ? "true" : "FALSE", v1, removed, bop.c_str(), tf);
    std::printf("  faces %d -> %d, edges %d -> %d\n",
                CountSub(base, TopAbs_FACE), CountSub(res, TopAbs_FACE),
                CountSub(base, TopAbs_EDGE), CountSub(res, TopAbs_EDGE));
    if (brepOut && *brepOut) {
      if (BRepTools::Write(res, brepOut)) std::printf("  wrote %s\n", brepOut);
    }
    std::printf("RESULT rot=%.3f r=%.3f dist=%.6f status=%s valid=%s vol=%.6f removed=%+.6f"
                " analytic=%.6f bop=%s secs=%.3f\n",
                rotDeg, radius, dVertex, verdict, valid ? "true" : "false", v1, removed, expect,
                clean ? "clean" : "DIRTY", tf);
    return 0;
  } catch (const Standard_Failure& e) {
    const double tf = Now() - tf0;
    std::printf("  RAISED %s: %s after %.3f s\n",
                e.DynamicType()->Name(), e.GetMessageString(), tf);
    std::printf("RESULT rot=%.3f r=%.3f dist=%.6f status=RAISED valid=- vol=- removed=-"
                " analytic=%.6f bop=- secs=%.3f\n", rotDeg, radius, dVertex, expect, tf);
    return 0;
  }
}

}  // namespace

int main(int argc, char** argv)
{
  // Unbuffered: a process killed by its deadline must still have shown every line it reached.
  std::setvbuf(stdout, NULL, _IONBF, 0);
  // Turn access violations into catchable Standard_Failure rather than a silent crash,
  // so "it died" is recorded as a measurement instead of an empty log.
  OSD::SetSignal(Standard_False);

  Standard_Real rot = 0.0, radius = 1.0;
  Standard_Real from = 0.0, to = 360.0, step = 15.0;
  const char* brepOut = NULL;
  int mode = 0;   // 0 = case, 1 = probe, 2 = identical
  Standard_Real idA = 0.0, idB = 90.0;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if      (a == "--case")     mode = 0;
    else if (a == "--probe")    mode = 1;
    else if (a == "--identical") {
      mode = 2;
      if (i + 2 < argc) { idA = std::atof(argv[i + 1]); idB = std::atof(argv[i + 2]); i += 2; }
    }
    else if (a == "--rot"      && i + 1 < argc) rot     = std::atof(argv[++i]);
    else if (a == "--radius"   && i + 1 < argc) radius  = std::atof(argv[++i]);
    else if (a == "--rot-from" && i + 1 < argc) from    = std::atof(argv[++i]);
    else if (a == "--rot-to"   && i + 1 < argc) to      = std::atof(argv[++i]);
    else if (a == "--rot-step" && i + 1 < argc) step    = std::atof(argv[++i]);
    else if (a == "--brep"     && i + 1 < argc) brepOut = argv[++i];
    else { std::printf("unknown argument: %s\n", a.c_str()); return 2; }
  }

  if (mode == 1) return Probe(from, to, step);
  if (mode == 2) return Identical(idA, idB);
  return Case(rot, radius, brepOut);
}
