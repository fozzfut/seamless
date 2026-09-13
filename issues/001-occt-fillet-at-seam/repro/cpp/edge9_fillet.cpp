// edge9_fillet.cpp
//
// THE OWNER'S OWN PART, on bare OCCT, with no FreeCAD anywhere in the process.
//
// The question this program exists to answer is the first one the owner will ask:
// "does Edge9 fillet now?" -- Edge9 being the straight top edge of his real part, the one
// whose end vertex the cylindrical pocket's seam lands on exactly (distance 0.000000000 mm,
// measured in docs/MEASUREMENTS.md section 5.2).
//
// WHY NOT THROUGH FREECAD. The same measurement has to be repeated against two kernels that
// differ by one line of ChFi3d_Builder_C1.cxx. Driving it through FreeCAD would mean copying
// the whole 2.1 GB installation to a scratch directory to put a patched TKFillet.dll next to
// it, and would leave FreeCAD's own layers (PartDesign, shape healing, TopoShape) inside the
// measurement. Reading the solid from a BREP file costs nothing and removes them.
// The solid comes out of the owner's document once, via repro/python/13_export_user_part.py,
// which copies the .FCStd first and never opens the original. Its volume after the BREP
// round trip differs from the volume in FreeCAD by 3.6e-12 mm3, so nothing is lost on the way.
//
// HOW THE EDGE IS IDENTIFIED. Not by index: "Edge9" is FreeCAD's name and there is no promise
// that OCCT's own edge map hands out the same order. The edge is found by its measured
// endpoints,
//     (24.999945, 19.347782, 10.0)  ->  (24.999945, 25.718401, 10.0)
// and the program refuses to run if the match is not unique. The endpoints come from the same
// export script, printed to nine decimals.
//
// A HANG IS A RESULT. Radii 0.5 and 0.55 did not return in FreeCAD after 9 minutes. So this
// program does ONE radius per process and prints unbuffered: the harness gives every process
// its own deadline and records a killed process as TIMEOUT, which is a measurement.
//
// USAGE
//   edge9_fillet --brep <file> --radius <r> [--p0 x,y,z] [--p1 x,y,z] [--out <result.brep>]
//   edge9_fillet --brep <file> --probe          list the edges, fillet nothing

#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <GProp_GProps.hxx>
#include <Geom_Curve.hxx>
#include <Geom_Surface.hxx>
#include <Standard_Failure.hxx>
#include <Standard_Version.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Shape.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Pnt.hxx>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace {

const Standard_Real PI_ = 3.14159265358979323846;

// The measured endpoints of Edge9 on the owner's part (13_export_user_part.py, section C).
Standard_Real P0[3] = { 24.999945, 19.347782, 10.0 };
Standard_Real P1[3] = { 24.999945, 25.718401, 10.0 };

double Now()
{
  using namespace std::chrono;
  return duration_cast<duration<double> >(steady_clock::now().time_since_epoch()).count();
}

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

Standard_Integer CountSub(const TopoDS_Shape& s, TopAbs_ShapeEnum t)
{
  TopTools_IndexedMapOfShape m;
  TopExp::MapShapes(s, t, m);
  return m.Extent();
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

// The C++ equivalent of FreeCAD Shape.check(True): the check that actually predicts whether
// a later boolean will work. Faults are counted by type; no spaces go into the verdict so
// the RESULT line stays parseable as key=value pairs.
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
      std::snprintf(buf, sizeof(buf), ",%s.x%d", it->first.c_str(), it->second);
      out += buf;
    }
    return out;
  } catch (const Standard_Failure& e) {
    clean = Standard_False;
    return std::string("RAISED.") + e.DynamicType()->Name();
  }
}

struct SeamHit { TopoDS_Edge edge; TopoDS_Face face; };

// A seam edge is one that BRep_Tool::IsClosed reports closed on its own face: the edge a
// periodic surface must carry, with two pcurves, one per branch.
std::vector<SeamHit> SeamEdges(const TopoDS_Shape& s)
{
  std::vector<SeamHit> out;
  for (TopExp_Explorer fx(s, TopAbs_FACE); fx.More(); fx.Next()) {
    const TopoDS_Face f = TopoDS::Face(fx.Current());
    for (TopExp_Explorer ex(f, TopAbs_EDGE); ex.More(); ex.Next()) {
      const TopoDS_Edge e = TopoDS::Edge(ex.Current());
      if (!BRep_Tool::IsClosed(e, f)) continue;
      Standard_Boolean seen = Standard_False;
      for (std::size_t i = 0; i < out.size(); ++i)
        if (out[i].edge.IsSame(e)) { seen = Standard_True; break; }
      if (!seen) { SeamHit h; h.edge = e; h.face = f; out.push_back(h); }
    }
  }
  return out;
}

Standard_Real DistToSeam(const TopoDS_Edge& e, const std::vector<SeamHit>& seams)
{
  Standard_Real best = -1.0;
  for (std::size_t i = 0; i < seams.size(); ++i) {
    try {
      BRepExtrema_DistShapeShape d(e, seams[i].edge);
      if (!d.IsDone()) continue;
      if (best < 0.0 || d.Value() < best) best = d.Value();
    } catch (const Standard_Failure&) {}
  }
  return best;
}

// Find the edge whose two endpoints are the ones measured in FreeCAD, in either order.
// The match must be unique: a non-unique match would silently move the measurement to a
// different edge and nothing downstream could tell.
Standard_Boolean FindEdgeByEnds(const TopoDS_Shape& s, Standard_Real tol,
                                TopoDS_Edge& out, Standard_Integer& index,
                                Standard_Integer& matches)
{
  const gp_Pnt a(P0[0], P0[1], P0[2]);
  const gp_Pnt b(P1[0], P1[1], P1[2]);
  TopTools_IndexedMapOfShape edges;
  TopExp::MapShapes(s, TopAbs_EDGE, edges);
  matches = 0;
  for (Standard_Integer i = 1; i <= edges.Extent(); ++i) {
    const TopoDS_Edge e = TopoDS::Edge(edges(i));
    TopoDS_Vertex v1, v2;
    TopExp::Vertices(e, v1, v2);
    if (v1.IsNull() || v2.IsNull()) continue;
    const gp_Pnt p1 = BRep_Tool::Pnt(v1), p2 = BRep_Tool::Pnt(v2);
    const Standard_Boolean fwd = p1.Distance(a) <= tol && p2.Distance(b) <= tol;
    const Standard_Boolean rev = p1.Distance(b) <= tol && p2.Distance(a) <= tol;
    if (!fwd && !rev) continue;
    ++matches;
    if (matches == 1) { out = e; index = i; }
  }
  return matches == 1;
}

// Volume a fillet of radius r must REMOVE along a straight edge of length L between two
// perpendicular faces: the corner left outside the quarter cylinder. Quoted as a sanity
// value, not as a tolerance -- the two ends of this particular edge are not both square.
Standard_Real AnalyticRemoved(Standard_Real r, Standard_Real length)
{
  return (1.0 - PI_ / 4.0) * r * r * length;
}

Standard_Boolean ParsePoint(const char* s, Standard_Real* p)
{
  return std::sscanf(s, "%lf,%lf,%lf", p, p + 1, p + 2) == 3;
}

int Probe(const TopoDS_Shape& base)
{
  TopTools_IndexedMapOfShape edges;
  TopExp::MapShapes(base, TopAbs_EDGE, edges);
  const std::vector<SeamHit> seams = SeamEdges(base);
  std::printf("  edges = %d, faces = %d, seam edges = %d\n",
              edges.Extent(), CountSub(base, TopAbs_FACE), (int)seams.size());
  for (Standard_Integer i = 1; i <= edges.Extent(); ++i) {
    const TopoDS_Edge e = TopoDS::Edge(edges(i));
    TopoDS_Vertex v1, v2;
    TopExp::Vertices(e, v1, v2);
    if (v1.IsNull() || v2.IsNull()) continue;
    const gp_Pnt p1 = BRep_Tool::Pnt(v1), p2 = BRep_Tool::Pnt(v2);
    Standard_Boolean isSeam = Standard_False;
    for (std::size_t k = 0; k < seams.size(); ++k)
      if (seams[k].edge.IsSame(e)) isSeam = Standard_True;
    std::printf("  edge %2d  len %9.6f  (%.6f, %.6f, %.6f) -> (%.6f, %.6f, %.6f)%s\n",
                i, EdgeLength(e), p1.X(), p1.Y(), p1.Z(), p2.X(), p2.Y(), p2.Z(),
                isSeam ? "  SEAM" : "");
  }
  return 0;
}

}  // namespace

int main(int argc, char** argv)
{
  // Unbuffered on purpose: a process killed by its deadline must still show every line it
  // reached, otherwise a hang leaves no evidence of how far it got.
  std::setvbuf(stdout, NULL, _IONBF, 0);

  const char* brep = NULL;
  const char* out = NULL;
  Standard_Real radius = 1.0;
  Standard_Boolean probe = Standard_False;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if      (a == "--brep"   && i + 1 < argc) brep   = argv[++i];
    else if (a == "--out"    && i + 1 < argc) out    = argv[++i];
    else if (a == "--radius" && i + 1 < argc) radius = std::atof(argv[++i]);
    else if (a == "--p0"     && i + 1 < argc) { if (!ParsePoint(argv[++i], P0)) { std::printf("bad --p0\n"); return 2; } }
    else if (a == "--p1"     && i + 1 < argc) { if (!ParsePoint(argv[++i], P1)) { std::printf("bad --p1\n"); return 2; } }
    else if (a == "--probe") probe = Standard_True;
    else { std::printf("unknown argument: %s\n", a.c_str()); return 2; }
  }
  if (!brep) { std::printf("--brep <file> is required\n"); return 2; }

  std::printf("OCCT %s -- the owner part, radius %.4f\n", OCC_VERSION_COMPLETE, radius);
  std::printf("  brep = %s\n", brep);

  TopoDS_Shape base;
  BRep_Builder builder;
  if (!BRepTools::Read(base, brep, builder) || base.IsNull()) {
    std::printf("RESULT r=%.4f status=BREP_READ_FAILED\n", radius);
    return 2;
  }

  const Standard_Real v0 = Volume(base);
  Standard_Boolean baseClean = Standard_False;
  const std::string baseBop = BopVerdict(base, baseClean);
  std::printf("  base solid: volume %.6f  faces %d  edges %d  valid %s  BOP %s\n",
              v0, CountSub(base, TopAbs_FACE), CountSub(base, TopAbs_EDGE),
              BRepCheck_Analyzer(base).IsValid() ? "true" : "FALSE", baseBop.c_str());

  if (probe) return Probe(base);

  TopoDS_Edge edge;
  Standard_Integer index = 0, matches = 0;
  if (!FindEdgeByEnds(base, 1.0e-4, edge, index, matches)) {
    std::printf("  endpoint match is not unique: %d edges matched\n", matches);
    std::printf("RESULT r=%.4f status=EDGE_NOT_FOUND matches=%d\n", radius, matches);
    return 2;
  }

  const std::vector<SeamHit> seams = SeamEdges(base);
  const Standard_Real len = EdgeLength(edge);
  const Standard_Real dist = DistToSeam(edge, seams);
  const Standard_Real expect = AnalyticRemoved(radius, len);
  std::printf("  target edge: OCCT index %d (FreeCAD Edge9)  length %.6f  dist(seam) %.9f\n",
              index, len, dist);
  std::printf("  analytic volume a correct fillet must REMOVE: %.6f mm3"
              "  -> ideal result %.6f\n", expect, v0 - expect);
  std::printf("  ... calling BRepFilletAPI_MakeFillet (a hang here IS the measurement) ...\n");

  const double t0 = Now();
  try {
    BRepFilletAPI_MakeFillet mk(base);
    mk.Add(radius, edge);
    mk.Build();
    const double tf = Now() - t0;

    if (!mk.IsDone()) {
      std::printf("  Build() reported NOT DONE after %.3f s\n", tf);
      std::printf("RESULT r=%.4f status=NOTDONE valid=- vol=- delta=- removed=- analytic=%.6f"
                  " bop=- secs=%.3f\n", radius, expect, tf);
      return 0;
    }

    const TopoDS_Shape res = mk.Shape();
    const Standard_Boolean valid = BRepCheck_Analyzer(res).IsValid();
    const Standard_Real v1 = Volume(res);
    Standard_Boolean clean = Standard_False;
    const std::string bop = BopVerdict(res, clean);
    const Standard_Real removed = v0 - v1;

    const char* verdict;
    if      (removed < 0.0)                              verdict = "BROKEN_VOLUME_GREW";
    else if (std::fabs(removed - expect) > 0.05 * expect) verdict = "BROKEN_WRONG_VOLUME";
    else if (!clean)                                     verdict = "BROKEN_BOP_DIRTY";
    else if (!valid)                                     verdict = "BROKEN_INVALID";
    else                                                 verdict = "OK";

    std::printf("  result: valid %s  volume %.6f  delta %+.6f  removed %+.6f mm3  BOP %s"
                "  fillet took %.3f s\n",
                valid ? "true" : "FALSE", v1, v1 - v0, removed, bop.c_str(), tf);
    std::printf("  faces %d -> %d, edges %d -> %d\n",
                CountSub(base, TopAbs_FACE), CountSub(res, TopAbs_FACE),
                CountSub(base, TopAbs_EDGE), CountSub(res, TopAbs_EDGE));
    if (out && *out) {
      if (BRepTools::Write(res, out)) std::printf("  wrote %s\n", out);
    }
    std::printf("RESULT r=%.4f status=%s valid=%s vol=%.6f delta=%+.6f removed=%+.6f"
                " analytic=%.6f ideal=%.6f bop=%s secs=%.3f\n",
                radius, verdict, valid ? "true" : "false", v1, v1 - v0, removed,
                expect, v0 - expect, clean ? "clean" : bop.c_str(), tf);
    return 0;
  } catch (const Standard_Failure& e) {
    const double tf = Now() - t0;
    std::printf("  RAISED %s: %s after %.3f s\n",
                e.DynamicType()->Name(), e.GetMessageString(), tf);
    std::printf("RESULT r=%.4f status=RAISED valid=- vol=- delta=- removed=- analytic=%.6f"
                " bop=- secs=%.3f\n", radius, expect, tf);
    return 0;
  }
}
