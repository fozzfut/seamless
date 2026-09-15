// mesh_params.cpp -- what ViewProviderPartExt::setupCoinGeometry (FreeCAD 1.1.1,
// src/Mod/Part/Gui/ViewProviderExt.cpp:1080-1110) asks of BRepMesh, timed on one shape, and which
// IMeshTools_Parameters change removes the cost.
//
//   mesh_params.exe <shape.brep> [face_index|0] [repeat]
//
// FreeCAD's call: Deflection = (dx+dy+dz)/300*Deviation of the whole object's bounding box
// (Part::Tools::getDeflection, Mod/Part/App/Tools.cpp:896), Relative=false, Angle=AngularDeflection,
// InParallel=true, AllowQualityDecrease=true, preceded by BRepTools::Clean(shape, true).
// Every configuration below starts from a cleaned shape. Output: seconds, triangles, nodes.
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepBndLib.hxx>
#include <BRepMesh_IncrementalMesh.hxx>
#include <IMeshTools_Parameters.hxx>
#include <Bnd_Box.hxx>
#include <Poly_Triangulation.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <Standard_Version.hxx>
#include <Geom_Surface.hxx>
#include <GeomAPI_ProjectPointOnSurf.hxx>
#include <algorithm>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

struct Config {
  const char* name;
  double angleDeg;
  double angleInteriorDeg;  // <= 0: OCCT default (2 * Angle)
  bool controlSurfaceDeflection;
  double minSizeFactor;     // <= 0: OCCT default; else MinSize = factor * Deflection
  bool delabella;
  bool parallel;
};

// Chordal error of the display mesh: for sampled triangles (every `step`-th of every face) the
// distance between the 3D centroid of the triangle and the surface point at the centroid of its UV
// nodes. This is the estimate BRepMesh itself uses for surface deflection, and what the eye sees as
// faceting. (A point projection onto the 1305-pole thread surfaces took minutes per configuration.)
static void chordError(const TopoDS_Shape& s, int step, double& maxErr, double& meanErr, long& samples)
{
  maxErr = meanErr = 0.0;
  samples = 0;
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next()) {
    const TopoDS_Face& f = TopoDS::Face(ex.Current());
    TopLoc_Location loc;
    Handle(Poly_Triangulation) t = BRep_Tool::Triangulation(f, loc);
    if (t.IsNull() || !t->HasUVNodes()) continue;
    TopLoc_Location sloc;
    Handle(Geom_Surface) surf = BRep_Tool::Surface(f, sloc);
    const gp_Trsf tr = loc.Transformation();
    const gp_Trsf strf = sloc.Transformation();
    for (int i = 1; i <= t->NbTriangles(); i += step) {
      int n1, n2, n3;
      t->Triangle(i).Get(n1, n2, n3);
      gp_Pnt p1 = t->Node(n1).Transformed(tr), p2 = t->Node(n2).Transformed(tr), p3 = t->Node(n3).Transformed(tr);
      gp_Pnt c((p1.X() + p2.X() + p3.X()) / 3, (p1.Y() + p2.Y() + p3.Y()) / 3, (p1.Z() + p2.Z() + p3.Z()) / 3);
      gp_Pnt2d u1 = t->UVNode(n1), u2 = t->UVNode(n2), u3 = t->UVNode(n3);
      gp_Pnt onSurf = surf->Value((u1.X() + u2.X() + u3.X()) / 3, (u1.Y() + u2.Y() + u3.Y()) / 3).Transformed(strf);
      double d = c.Distance(onSurf);
      maxErr = std::max(maxErr, d);
      meanErr += d;
      ++samples;
    }
  }
  if (samples) meanErr /= samples;
}

static void count(const TopoDS_Shape& s, long& tri, long& nodes, int& nullFaces)
{
  tri = nodes = 0;
  nullFaces = 0;
  for (TopExp_Explorer ex(s, TopAbs_FACE); ex.More(); ex.Next()) {
    TopLoc_Location loc;
    Handle(Poly_Triangulation) t = BRep_Tool::Triangulation(TopoDS::Face(ex.Current()), loc);
    if (t.IsNull()) {
      ++nullFaces;
      continue;
    }
    tri += t->NbTriangles();
    nodes += t->NbNodes();
  }
}

int main(int argc, char** argv)
{
  if (argc < 2) {
    std::printf("usage: mesh_params <shape.brep> [face_index|0] [repeat]\n");
    return 2;
  }
  TopoDS_Shape whole;
  BRep_Builder bb;
  if (!BRepTools::Read(whole, argv[1], bb)) {
    std::printf("cannot read %s\n", argv[1]);
    return 2;
  }
  int faceIndex = argc > 2 ? std::atoi(argv[2]) : 0;
  int repeat = argc > 3 ? std::atoi(argv[3]) : 1;

  // deflection always from the WHOLE object, as the view provider does
  Bnd_Box box;
  BRepBndLib::Add(whole, box);
  box.SetGap(0.0);
  double x0, y0, z0, x1, y1, z1;
  box.Get(x0, y0, z0, x1, y1, z1);
  const double deviation = 0.5;
  const double deflection = ((x1 - x0) + (y1 - y0) + (z1 - z0)) / 300.0 * deviation;

  TopoDS_Shape target = whole;
  if (faceIndex > 0) {
    TopTools_IndexedMapOfShape faces;
    TopExp::MapShapes(whole, TopAbs_FACE, faces);
    target = faces(faceIndex);
  }
  std::printf("OCCT %s, deflection %.6f, target %s\n", OCC_VERSION_COMPLETE, deflection,
              faceIndex > 0 ? ("face " + std::to_string(faceIndex)).c_str() : "whole shape");

  const double ANG = 6.4000000953674316;  // the value stored in the owner's GuiDocument.xml
  std::vector<Config> configs = {
      {"freecad_6.4_stored", ANG, 0, true, 0, false, true},
      {"freecad_28.5_default", 28.5, 0, true, 0, false, true},
      {"freecad_15", 15.0, 0, true, 0, false, true},
      {"freecad_10", 10.0, 0, true, 0, false, true},
      {"15_csd_off", 15.0, 0, false, 0, false, true},
      {"28.5_csd_off", 28.5, 0, false, 0, false, true},
      {"6.4_csd_off", ANG, 0, false, 0, false, true},
      {"6.4_interior_28.5", ANG, 28.5, true, 0, false, true},
      {"6.4_interior_57", ANG, 57.0, true, 0, false, true},
      {"6.4_minsize_1defl", ANG, 0, true, 1.0, false, true},
      {"6.4_delabella", ANG, 0, true, 0, true, true},
      {"6.4_delabella_csd_off", ANG, 0, false, 0, true, true},
      {"6.4_serial", ANG, 0, true, 0, false, false},
  };
  if (const char* only = std::getenv("MESH_ONLY")) {
    std::vector<Config> kept;
    for (auto& c : configs)
      if (std::string(only).find(c.name) != std::string::npos) kept.push_back(c);
    configs = kept;
  }

  for (const auto& c : configs) {
    for (int r = 0; r < repeat; ++r) {
      TopoDS_Shape s = target;
      BRepTools::Clean(s, Standard_True);
      IMeshTools_Parameters p;
      p.Deflection = deflection;
      p.Relative = Standard_False;
      p.Angle = c.angleDeg * M_PI / 180.0;
      if (c.angleInteriorDeg > 0) p.AngleInterior = c.angleInteriorDeg * M_PI / 180.0;
      p.InParallel = c.parallel;
      p.AllowQualityDecrease = Standard_True;
      p.ControlSurfaceDeflection = c.controlSurfaceDeflection;
      if (c.minSizeFactor > 0) p.MinSize = c.minSizeFactor * deflection;
      if (c.delabella) p.MeshAlgo = IMeshTools_MeshAlgoType_Delabella;
      auto t0 = std::chrono::steady_clock::now();
      BRepMesh_IncrementalMesh mesher(s, p);
      auto t1 = std::chrono::steady_clock::now();
      long tri, nodes;
      int nullFaces;
      count(s, tri, nodes, nullFaces);
      double maxErr = -1, meanErr = -1;
      long samples = 0;
      if (std::getenv("MESH_QUALITY") && r == 0) chordError(s, 7, maxErr, meanErr, samples);
      std::printf("%-26s run%d  %9.3f s  triangles %9ld  nodes %9ld  unmeshed_faces %d  status %d"
                  "  chord_max %.4f  chord_mean %.5f  (samples %ld, deflection %.4f)\n", c.name, r,
                  std::chrono::duration<double>(t1 - t0).count(), tri, nodes, nullFaces, mesher.GetStatusFlags(),
                  maxErr, meanErr, samples, deflection);
      std::fflush(stdout);
    }
  }
  return 0;
}
