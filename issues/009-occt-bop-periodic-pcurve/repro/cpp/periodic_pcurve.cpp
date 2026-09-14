// periodic_pcurve: synthetic reproduction of defect 009 (OCCT 7.8.1, BOPTools_AlgoTools2D::AdjustPCurveOnSurf).
//
// A solid cylinder R15 x 10 is built and its side face moved exactly to the UV domain [-pi, pi]; then the
// pcurve of its top circle on the side face is replaced by a straight segment that starts and ends 2e-5 rad
// beyond the seam lines u = -pi / u = pi (edge tolerance raised to 1e-3 so the edge stays within tolerance:
// 2e-5 * 15 = 3e-4 mm). The side face's UV bounds are then 4e-5 wider than the period, which is what a STEP
// import delivers for helical strips (measured up to 6.3e-5 rad on a real threaded part). A box whose face
// y = +8 crosses the side face at u = -2.5791 and u = -0.5625 (the plane/cylinder intersection gives them in
// [0, 2pi): 3.7041 and 5.7207, i.e. both need a shift of -2pi) is cut.
//
// usage: periodic_pcurve [out.brep]   - prints numbers and a verdict line PERIODIC-PCURVE: BROKEN | FIXED
#define _USE_MATH_DEFINES
#include <cmath>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_Copy.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepBuilderAPI_Sewing.hxx>
#include <BRepLib.hxx>
#include <BSplCLib.hxx>
#include <TColStd_Array1OfReal.hxx>
#include <gp_Pln.hxx>
#include <gp_Ax3.hxx>
#include <TopExp.hxx>
#include <TopoDS_Wire.hxx>
#include <TopoDS_Shell.hxx>
#include <TopoDS_Solid.hxx>
#include <TopoDS_Vertex.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Ax1.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <GCE2d_MakeSegment.hxx>
#include <Geom2dConvert.hxx>
#include <Geom2d_BSplineCurve.hxx>
#include <Geom2d_TrimmedCurve.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <Geom_Circle.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <Standard_Failure.hxx>
#include <Standard_Version.hxx>
#include <iostream>

static double vol(const TopoDS_Shape& s) { GProp_GProps p; BRepGProp::VolumeProperties(s, p); return p.Mass(); }
static int nsolids(const TopoDS_Shape& s) { int n = 0; for (TopExp_Explorer e(s, TopAbs_SOLID); e.More(); e.Next()) ++n; return n; }

static TopoDS_Shape overshooting_cylinder(double overshoot, double& widthOver) {
  BRep_Builder bb;
  gp_Ax2 ax(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0));
  TopoDS_Shape cyl = BRepBuilderAPI_Copy(BRepPrimAPI_MakeCylinder(ax, 15.0, 10.0).Shape()).Shape();
  widthOver = 0;
  for (TopExp_Explorer fe(cyl, TopAbs_FACE); fe.More(); fe.Next()) {
    TopoDS_Face f = TopoDS::Face(fe.Current());
    f.Orientation(TopAbs_FORWARD);
    TopLoc_Location loc;
    Handle(Geom_CylindricalSurface) cs = Handle(Geom_CylindricalSurface)::DownCast(BRep_Tool::Surface(f, loc));
    if (cs.IsNull()) continue;
    // 1. the same geometry with the UV domain [-pi, pi]: every pcurve moves by -pi and the surface frame turns
    //    by +pi about its axis, S'(u) = S(u + pi) - exact, nothing moves in space
    TopTools_IndexedMapOfShape edges; TopExp::MapShapes(f, TopAbs_EDGE, edges);
    for (int i = 1; i <= edges.Extent(); ++i) {
      TopoDS_Edge e = TopoDS::Edge(edges(i));
      double tol = BRep_Tool::Tolerance(e);
      if (BRep_Tool::IsClosed(e, f)) {
        TopoDS_Edge ef = e; ef.Orientation(TopAbs_FORWARD);
        TopoDS_Edge er = e; er.Orientation(TopAbs_REVERSED);
        double a, b;
        Handle(Geom2d_Curve) c1 = Handle(Geom2d_Curve)::DownCast(BRep_Tool::CurveOnSurface(ef, f, a, b)->Copy());
        Handle(Geom2d_Curve) c2 = Handle(Geom2d_Curve)::DownCast(BRep_Tool::CurveOnSurface(er, f, a, b)->Copy());
        c1->Translate(gp_Vec2d(-M_PI, 0)); c2->Translate(gp_Vec2d(-M_PI, 0));
        bb.UpdateEdge(ef, c1, c2, f, tol);
      } else if (!BRep_Tool::Degenerated(e)) {
        double a, b;
        Handle(Geom2d_Curve) c = Handle(Geom2d_Curve)::DownCast(BRep_Tool::CurveOnSurface(e, f, a, b)->Copy());
        c->Translate(gp_Vec2d(-M_PI, 0));
        bb.UpdateEdge(e, c, f, tol);
      }
    }
    gp_Ax3 pos = cs->Position();
    pos.Rotate(gp_Ax1(pos.Location(), pos.Direction()), M_PI);
    cs->SetPosition(pos);
    double u0, u1, v0, v1; BRepTools::UVBounds(f, u0, u1, v0, v1);
    std::cout << "side face moved to UV [" << u0 << ", " << u1 << "]; solid valid " << BRepCheck_Analyzer(cyl).IsValid()
              << " volume " << vol(cyl) << "\n";
    // 2. the top circle's pcurve overshoots both seam lines by `overshoot` (edge tolerance 1e-3 covers 15 * 2e-5)
    for (int i = 1; i <= edges.Extent(); ++i) {
      TopoDS_Edge e = TopoDS::Edge(edges(i));
      if (BRep_Tool::IsClosed(e, f) || BRep_Tool::Degenerated(e)) continue;
      double a, b; Handle(Geom2d_Curve) c = BRep_Tool::CurveOnSurface(e, f, a, b);
      gp_Pnt2d pa = c->Value(a), pb = c->Value(b);
      if (std::abs(pa.Y() - v1) > 1e-9) continue;
      double sa = pa.X() < pb.X() ? -overshoot : overshoot;
      gp_Pnt2d qa(pa.X() + sa, pa.Y()), qb(pb.X() - sa, pb.Y());
      Handle(Geom2d_BSplineCurve) seg = Geom2dConvert::CurveToBSplineCurve(GCE2d_MakeSegment(qa, qb).Value());
      TColStd_Array1OfReal knots(1, seg->NbKnots()); seg->Knots(knots);
      BSplCLib::Reparametrize(a, b, knots); seg->SetKnots(knots);
      bb.UpdateEdge(e, seg, f, 1e-3);
      for (TopExp_Explorer ve(e, TopAbs_VERTEX); ve.More(); ve.Next()) bb.UpdateVertex(TopoDS::Vertex(ve.Current()), 1e-3);
    }
    double w0, w1, w2, w3; BRepTools::UVBounds(f, w0, w1, w2, w3);
    widthOver = (w1 - w0) - 2 * M_PI;
    std::cout << "side face UV bounds [" << w0 << ", " << w1 << "], wider than the period by " << widthOver << "\n";
  }
  return cyl;
}

int main(int argc, char** argv) {
  std::cout.precision(10);
  std::cout << "OCCT " << OCC_VERSION_COMPLETE << "\n";
  try {
    // the box face y = +8 meets the side face where u = -2.5791 and -0.5625 in its [-pi, pi] domain; the
    // plane/cylinder intersection delivers them as 3.7041 and 5.7207, so both need a period shift
    TopoDS_Shape box = BRepPrimAPI_MakeBox(gp_Pnt(-30, -30, -5), gp_Pnt(30, 8, 15)).Shape();
    double exactRemoved = 0;
    {
      gp_Ax2 ax(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(-1, 0, 0));
      TopoDS_Shape clean = BRepPrimAPI_MakeCylinder(ax, 15.0, 10.0).Shape();
      exactRemoved = vol(BRepAlgoAPI_Common(box, clean).Shape());
      std::cout << "clean cylinder: common " << exactRemoved << " (analytic 10 * (pi*225 - segment) = "
                << 10.0 * (M_PI * 225.0 - (225.0 * std::acos(8.0 / 15.0) - 8.0 * std::sqrt(225.0 - 64.0))) << ")\n";
    }
    double over = 0;
    TopoDS_Shape tool = overshooting_cylinder(2e-5, over);
    std::cout << "tool valid " << BRepCheck_Analyzer(tool).IsValid() << " volume " << vol(tool) << "\n";
    if (argc > 1) BRepTools::Write(tool, argv[1]);
    double vb = vol(box), vt = vol(tool);
    TopoDS_Shape cut = BRepAlgoAPI_Cut(box, tool).Shape();
    TopoDS_Shape com = BRepAlgoAPI_Common(box, tool).Shape();
    TopoDS_Shape fus = BRepAlgoAPI_Fuse(box, tool).Shape();
    double vc = vol(cut), vm = vol(com), vf = vol(fus);
    std::cout << "cut " << vc << " (" << nsolids(cut) << " solids)  common " << vm << " (" << nsolids(com)
              << " solids)  fuse " << vf << " (" << nsolids(fus) << " solids)\n";
    double e1 = std::abs(vc + vm - vb), e2 = std::abs(vb + vt - vm - vf), e3 = std::abs(vm - exactRemoved);
    std::cout << "|cut+common-box| " << e1 << "  |box+tool-common-fuse| " << e2 << "  |common-exact| " << e3 << "\n";
    bool fixed = over > 0 && e1 < 1.0 && e2 < 1.0 && e3 < 1.0;
    std::cout << "PERIODIC-PCURVE: " << (over <= 0 ? "NOT REPRODUCED (no overshoot)" : fixed ? "FIXED" : "BROKEN") << "\n";
    return 0;
  } catch (Standard_Failure& f) {
    std::cout << "OCCT exception: " << f.GetMessageString() << "\nPERIODIC-PCURVE: EXCEPTION\n";
    return 1;
  }
}
