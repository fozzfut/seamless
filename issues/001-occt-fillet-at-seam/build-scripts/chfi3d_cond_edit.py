#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edit src/ChFi3d/ChFi3d_Builder_C1.cxx of a pristine V7_8_1 tree in one of three ways:

    trace   stock behaviour + a measurement trace at the ChFi3d_Recale call site
            (prints only when the environment variable SEAM_TRACE is set)
    cond    the narrowed guard (patches/0002-*.patch)
    blunt   the guard simply dropped (patches/0001-*.patch) -- kept so that the
            regression this work exists to remove can be reproduced on demand,
            in the same tree, as a control
    stock   restore the pristine file

Every edit is an exact, asserted-unique string replacement, so a silently missed
edit is impossible.  Usage:  chfi3d_cond_edit.py <mode> [<occt-src-root>]
"""
import hashlib
import shutil
import sys
import os

PRISTINE_MD5 = "908581ebdfb6dc5fa8914a027299210f"

ANCHOR = "    if (onsame) ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));\n"

INC_ANCHOR = "#include <BRepTools.hxx>\n"
INC_TRACE = "#include <BRepTools.hxx>\n#include <cstdio>\n#include <cstdlib>\n"

TRACE = r'''    // ---- seamless project: MEASUREMENT TRACE, not for upstream ---------------
    // Prints, at the ChFi3d_Recale call site, everything the narrowing condition
    // could possibly be built from.  Silent unless SEAM_TRACE is set in the
    // environment, so the same DLL is a stock kernel for every other run.
    {
      if (getenv("SEAM_TRACE") != NULL) {
        Handle(Geom_Surface) aTrSurf = Bs.ChangeSurface().Surface();
        Handle(Geom_RectangularTrimmedSurface) aTrRts =
          Handle(Geom_RectangularTrimmedSurface)::DownCast(aTrSurf);
        Handle(Geom_Surface) aTrBasis = aTrSurf;
        if (!aTrRts.IsNull()) aTrBasis = aTrRts->BasisSurface();
        Standard_Real ub1, ub2, vb1, vb2;
        aTrBasis->Bounds(ub1, ub2, vb1, vb2);
        Standard_Real fu, lu, fv, lv;
        BRepTools::UVBounds(Fv, fu, lu, fv, lv);
        Standard_Real uper = aTrBasis->IsUPeriodic() ? aTrBasis->UPeriod() : 0.;
        Standard_Real vper = aTrBasis->IsVPeriodic() ? aTrBasis->VPeriod() : 0.;
        Standard_Integer nUseam = 0, nVseam = 0, nDegSeam = 0;
        TopLoc_Location aTrLoc;
        Handle(Geom_Surface) aTrFaceSurf = BRep_Tool::Surface(Fv, aTrLoc);
        TopExp_Explorer aTrEx;
        for (aTrEx.Init(Fv, TopAbs_EDGE); aTrEx.More(); aTrEx.Next()) {
          const TopoDS_Edge& aTrE = TopoDS::Edge(aTrEx.Current());
          if (!BRep_Tool::IsClosed(aTrE, aTrFaceSurf, aTrLoc)) continue;
          if (BRep_Tool::Degenerated(aTrE)) { nDegSeam++; continue; }
          Standard_Real w1, w2;
          Handle(Geom2d_Curve) cF = BRep_Tool::CurveOnSurface
            (TopoDS::Edge(aTrE.Oriented(TopAbs_FORWARD)), Fv, w1, w2);
          Handle(Geom2d_Curve) cR = BRep_Tool::CurveOnSurface
            (TopoDS::Edge(aTrE.Oriented(TopAbs_REVERSED)), Fv, w1, w2);
          if (cF.IsNull() || cR.IsNull()) continue;
          gp_Pnt2d pA = cF->Value(0.5 * (w1 + w2));
          gp_Pnt2d pB = cR->Value(0.5 * (w1 + w2));
          if (Abs(pA.X() - pB.X()) > Abs(pA.Y() - pB.Y())) nUseam++; else nVseam++;
        }
        Standard_Boolean aTrCout = Standard_False;
        TopoDS_Edge aTrEc;
        ChFi3d_Couture(Fv, aTrCout, aTrEc);
        printf("SEAMTRACE onsame=%d IFadArc=%d isfirst=%d\n", (int)onsame, (int)IFadArc, (int)isfirst);
        printf("SEAMTRACE   Bs.face_is_Fv=%d Bs.IsUPeriodic=%d Bs.IsUClosed=%d "
               "Bs.IsVPeriodic=%d Bs.IsVClosed=%d\n",
               (int)Bs.Face().IsSame(Fv), (int)Bs.IsUPeriodic(), (int)Bs.IsUClosed(),
               (int)Bs.IsVPeriodic(), (int)Bs.IsVClosed());
        printf("SEAMTRACE   Bs.range U=[%.9f %.9f] V=[%.9f %.9f]\n",
               Bs.FirstUParameter(), Bs.LastUParameter(),
               Bs.FirstVParameter(), Bs.LastVParameter());
        printf("SEAMTRACE   face.UVBounds U=[%.9f %.9f] V=[%.9f %.9f] spanU=%.9f spanV=%.9f\n",
               fu, lu, fv, lv, lu - fu, lv - fv);
        printf("SEAMTRACE   surf=%s basis=%s trimmed=%d\n",
               aTrSurf->DynamicType()->Name(), aTrBasis->DynamicType()->Name(),
               (int)(!aTrRts.IsNull()));
        printf("SEAMTRACE   basis.IsUPeriodic=%d UPeriod=%.9f basis.IsVPeriodic=%d VPeriod=%.9f "
               "basis.IsUClosed=%d basis.IsVClosed=%d basis.bounds U=[%.9f %.9f] V=[%.9f %.9f]\n",
               (int)aTrBasis->IsUPeriodic(), uper, (int)aTrBasis->IsVPeriodic(), vper,
               (int)aTrBasis->IsUClosed(), (int)aTrBasis->IsVClosed(), ub1, ub2, vb1, vb2);
        printf("SEAMTRACE   seam_edges: U=%d V=%d degenerate=%d ChFi3d_Couture=%d\n",
               nUseam, nVseam, nDegSeam, (int)aTrCout);
        printf("SEAMTRACE   pfac1=(%.9f %.9f) pfac2=(%.9f %.9f) du=%.9f dv=%.9f\n",
               pfac1.X(), pfac1.Y(), pfac2.X(), pfac2.Y(),
               Abs(pfac2.X() - pfac1.X()), Abs(pfac2.Y() - pfac1.Y()));
        if (uper > 0.) {
          Standard_Real u1 = pfac1.X(), u2 = pfac2.X(), nu1 = u1, nu2 = u2;
          Standard_Boolean fires = (Abs(u2 - u1) > 0.5 * uper);
          if (fires) {
            if      (u2 < u1 &&  (IFadArc == 1)) nu2 = u2 + uper;
            else if (u2 < u1 && !(IFadArc == 1)) nu1 = u1 - uper;
            else if (u1 < u2 &&  (IFadArc == 1)) nu2 = u2 - uper;
            else if (u1 < u2 && !(IFadArc == 1)) nu1 = u1 + uper;
          }
          printf("SEAMTRACE   recale_U_would_fire=%d -> u1=%.9f u2=%.9f inside_face=%d%d\n",
                 (int)fires, nu1, nu2,
                 (int)(nu1 >= fu - 1.e-7 && nu1 <= lu + 1.e-7),
                 (int)(nu2 >= fu - 1.e-7 && nu2 <= lu + 1.e-7));
        }
        fflush(stdout);
      }
    }
    // ---- end of measurement trace -------------------------------------------
'''

# The narrowed guard.  The text lives here so the .patch file and the built DLL
# can never drift apart: the patch is produced from this tree by git diff.
COND = r'''    // pfac1 and pfac2 are two 2d points on the same face Bs at the end of the
    // fillet. When that face carries a seam they can be returned on the two
    // different branches of the seam pcurve - u and u + period are the same 3d
    // point, so no check downstream notices - and the trim window built from
    // them below (ChFi3d_Boite/ChFi3d_BoundFac) then does not contain the corner
    // vertex. ChFi3d_Recale is the helper that brings them back to one branch.
    //
    // onsame: the state in which ChFi3d_Recale was called until now. Kept first
    // so that the OnSame path, where Bs is loaded without restriction
    // (Bs.Initialize(Fv,Standard_False) above) and its IsUClosed would not be
    // the face's own answer, keeps its old behaviour exactly.
    //
    // IsUClosed/IsVClosed: the adaptor's test for "the face trim spans the whole
    // period", which is what having a seam edge means. It is needed because
    // ChFi3d_Recale looks at the periodicity of the BASIS surface, after the
    // trim is discarded, and its "more than half a period apart" test is then
    // met by two perfectly legal points on a face that is periodic but not
    // closed. Measured at this line, stock 7.8.1, three corners:
    //   cylindrical face with a seam on the corner vertex (the reported defect):
    //     face U range [0, 6.283185307] = UPeriod, IsUClosed True, 2 seam edges,
    //     pfac1.X 6.176614355, pfac2.X 0.106570952, |du| 6.070043402;
    //     ChFi3d_Recale moves pfac2.X to 6.389756260, i.e. onto the branch of
    //     pfac1, and the corner is then found.
    //   270 degree surface of revolution (tests blend/simple/H4 and
    //   blend/buildevol/D6): face U range [0, 4.712388980] = 3/4 of UPeriod,
    //     IsUClosed False, no seam edge, pfac1.X 0, pfac2.X 4.712388980,
    //     |du| 4.712388980 > 0.5*UPeriod; calling ChFi3d_Recale here moves
    //     pfac2.X to -1.570796327, a whole period outside the face, and the
    //     resulting shell is unorientable and not closed.
    if (onsame || Bs.IsUClosed() || Bs.IsVClosed())
      ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));
'''


def read(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8", "surrogateescape")


def write(p, s):
    with open(p, "wb") as f:
        f.write(s.encode("utf-8", "surrogateescape"))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    root = sys.argv[2] if len(sys.argv) > 2 else "C:/dev/occt-cond"
    path = os.path.join(root, "src", "ChFi3d", "ChFi3d_Builder_C1.cxx")
    orig = path + ".pristine"
    if not os.path.exists(orig):
        shutil.copyfile(path, orig)
    got = hashlib.md5(read(orig).encode("utf-8", "surrogateescape")).hexdigest()
    if got != PRISTINE_MD5:
        sys.exit("pristine copy is not V7_8_1: md5 %s != %s" % (got, PRISTINE_MD5))
    src = read(orig)
    if mode == "stock":
        out = src
    elif mode == "trace":
        assert src.count(INC_ANCHOR) == 1, "include anchor not unique"
        assert src.count(ANCHOR) == 1, "call-site anchor not unique"
        out = src.replace(INC_ANCHOR, INC_TRACE).replace(ANCHOR, TRACE + ANCHOR)
    elif mode == "cond":
        assert src.count(ANCHOR) == 1, "call-site anchor not unique"
        out = src.replace(ANCHOR, COND)
    elif mode == "blunt":
        assert src.count(ANCHOR) == 1, "call-site anchor not unique"
        out = src.replace(ANCHOR,
                          "    ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));\n")
    else:
        sys.exit("usage: chfi3d_cond_edit.py {stock|trace|cond} [occt-src-root]")
    write(path, out)
    print("%s -> %s  md5 %s" % (mode, path,
          hashlib.md5(out.encode("utf-8", "surrogateescape")).hexdigest()))


if __name__ == "__main__":
    main()
