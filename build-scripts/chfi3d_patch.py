#!/usr/bin/env python3
"""chfi3d_patch.py -- apply / revert the seam-fillet instrumentation and fix to an OCCT
source tree, reproducibly and by exact anchor, never by line number.

WHY A SCRIPT AND NOT A .patch FILE: a unified diff is matched by context and silently
rots when anything above it moves. This script locates every insertion point by the
STRIPPED TEXT of a unique line inside a NAMED FUNCTION, asserts the match is unique, and
refuses to write anything if any anchor is missing or ambiguous. A half-applied patch to
a 6000-line file would be far worse than no patch.

It always rebuilds from the pristine backup, so applying `trace` after `fix` cannot stack
two copies of the same insertion.

WHICH TREE IT EDITS: $OCCT_SRC (default C:/dev/occt-fix/src/ChFi3d) -- a PRIVATE copy.
The shared clone at C:/dev/seamless/occt is being edited by another agent team at the
same time; two writers on one 6000-line file produce measurements nobody can attribute.

  python chfi3d_patch.py backup            take the pristine copy (once)
  python chfi3d_patch.py revert            restore pristine
  python chfi3d_patch.py trace             instrumentation only
  python chfi3d_patch.py fix [false]       the fix only (`false` => refon1 = False)
  python chfi3d_patch.py trace fix         both
  python chfi3d_patch.py status
"""

import os
import shutil
import sys

SRC = os.environ.get("OCCT_SRC", r"C:\dev\occt-fix\src\ChFi3d")
BACKUP = os.environ.get("OCCT_SRC_BACKUP", r"C:\dev\seamless\build\occt-src-orig")
FILES = ["ChFi3d_Builder.cxx", "ChFi3d_Builder_C1.cxx"]

BASE_HELPER = r"""
// ---------------------------------------------------------------------------
// seam-fillet investigation, 2026-09-12. Tracing of the corner decisions.
// Inert unless the environment variable CHFI3D_TRACE is set (and not "0"), so one DLL
// serves both for measuring and for shipping.
// ---------------------------------------------------------------------------
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

static int chfi3d_trace_on()
{
  static int t = -1;
  if (t < 0) {
    const char* e = getenv("CHFI3D_TRACE");
    t = (e && *e && *e != '0') ? 1 : 0;
  }
  return t;
}

static void chfi3d_tr(const char* fmt, ...)
{
  if (!chfi3d_trace_on()) return;
  va_list ap;
  va_start(ap, fmt);
  vfprintf(stdout, fmt, ap);
  va_end(ap);
  fflush(stdout);   // unbuffered: a case killed by its deadline still keeps its trace
}

// ---------------------------------------------------------------------------

"""

SURF_HELPER = r"""
static void chfi3d_tr_surf(const char* tag, BRepAdaptor_Surface& theBs)
{
  if (!chfi3d_trace_on()) return;
  Handle(Geom_Surface) s = theBs.ChangeSurface().Surface();
  Handle(Geom_RectangularTrimmedSurface) t =
    Handle(Geom_RectangularTrimmedSurface)::DownCast(s);
  if (!t.IsNull()) s = t->BasisSurface();
  Standard_Real u1 = 0., u2 = 0., v1 = 0., v2 = 0.;
  s->Bounds(u1, u2, v1, v2);
  chfi3d_tr("[CHFI3D]   %s = %s  uperiodic=%s uperiod=%.9f  bounds u[%.6f %.6f] v[%.6f %.6f]\n",
            tag, s->DynamicType()->Name(),
            s->IsUPeriodic() ? "YES" : "no",
            s->IsUPeriodic() ? s->UPeriod() : 0.0, u1, u2, v1, v2);
}
"""


class Anchors:
    """Line-based editor: every edit names a unique stripped line inside a range."""

    def __init__(self, path):
        self.path = path
        with open(path, "r", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            self.text = f.read()
        self.nl = "\r\n" if "\r\n" in self.text else "\n"
        self.lines = self.text.split(self.nl)
        self.edits = 0

    def func_start(self, sig_prefix):
        starts = [i for i, l in enumerate(self.lines) if l.startswith(sig_prefix)]
        if len(starts) != 1:
            raise SystemExit("ANCHOR FAIL %s: %r found %d times (want 1)"
                             % (self.path, sig_prefix, len(starts)))
        return starts[0]

    def func_range(self, sig_prefix):
        s = self.func_start(sig_prefix)
        for j in range(s + 1, len(self.lines)):
            if self.lines[j].startswith(("void ChFi3d_Builder::",
                                         "Standard_Boolean ChFi3d_Builder::",
                                         "//function :")):
                return s, j
        return s, len(self.lines)

    def find(self, stripped, lo=0, hi=None):
        hi = len(self.lines) if hi is None else hi
        hits = [i for i in range(lo, hi) if self.lines[i].strip() == stripped]
        if len(hits) != 1:
            raise SystemExit("ANCHOR FAIL %s: %r found %d times in [%d,%d) (want 1)"
                             % (self.path, stripped, len(hits), lo, hi))
        return hits[0]

    def _body(self, block):
        b = block.split("\n")
        if b and b[-1] == "":
            b.pop()
        return b

    def insert_after(self, idx, block):
        b = self._body(block)
        self.lines[idx + 1:idx + 1] = b
        self.edits += 1
        return len(b)

    def insert_before(self, idx, block):
        b = self._body(block)
        self.lines[idx:idx] = b
        self.edits += 1
        return len(b)

    def save(self):
        with open(self.path, "w", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            f.write(self.nl.join(self.lines))


def do_backup(force=False):
    os.makedirs(BACKUP, exist_ok=True)
    for f in FILES:
        dst = os.path.join(BACKUP, f)
        if os.path.exists(dst) and not force:
            continue
        shutil.copy2(os.path.join(SRC, f), dst)
        print("backed up %s -> %s" % (f, dst))


def do_revert():
    for f in FILES:
        src = os.path.join(BACKUP, f)
        if not os.path.exists(src):
            raise SystemExit("no backup for %s -- run `backup` first" % f)
        shutil.copy2(src, os.path.join(SRC, f))


def patch_builder(trace):
    """ChFi3d_Builder.cxx: which corner routine is this vertex sent to?"""
    if not trace:
        return 0
    a = Anchors(os.path.join(SRC, "ChFi3d_Builder.cxx"))
    fs = a.func_start("void ChFi3d_Builder::PerformFilletOnVertex")
    a.insert_before(max(fs - 4, 0), BASE_HELPER)
    fs, fe = a.func_range("void ChFi3d_Builder::PerformFilletOnVertex")
    i = a.find("Standard_Integer nba = ChFi3d_NumberOfSharpEdges(Vtx, myVEMap, myEFMap);",
               fs, fe)
    a.insert_after(i, r"""  if (chfi3d_trace_on()) {
    gp_Pnt aTrP = BRep_Tool::Pnt(Vtx);
    chfi3d_tr("[CHFI3D] ===== PerformFilletOnVertex Index=%d vertex=(%.6f, %.6f, %.6f)\n",
              Index, aTrP.X(), aTrP.Y(), aTrP.Z());
    chfi3d_tr("[CHFI3D]   stripes i=%d  nba(sharp edges)=%d  nondegenere=%s -> %s\n",
              i, nba, nondegenere ? "yes" : "no",
              (nba > 3) ? "PerformIntersectionAtEnd (nba>3)"
                        : "PerformOneCorner / PerformMoreSurfdata (nba<=3)");
  }
""")
    a.save()
    return a.edits


def patch_c1(trace, fix, refon1):
    a = Anchors(os.path.join(SRC, "ChFi3d_Builder_C1.cxx"))

    if trace:
        # helper must precede the first function it is used from (PerformOneCorner)
        fs = a.func_start("void ChFi3d_Builder::PerformOneCorner")
        a.insert_before(max(fs - 12, 0), BASE_HELPER + SURF_HELPER)

    # ---------------- PerformOneCorner ----------------
    fs, fe = a.func_range("void ChFi3d_Builder::PerformOneCorner")

    if trace:
        i = a.find("Standard_Boolean onsame = (stat == ChFiDS_OnSame);", fs, fe)
        n = a.insert_after(i, r"""  if (chfi3d_trace_on()) {
    gp_Pnt aTrP = BRep_Tool::Pnt(Vtx);
    chfi3d_tr("[CHFI3D] ENTER PerformOneCorner Index=%d vertex=(%.6f, %.6f, %.6f)\n",
              Index, aTrP.X(), aTrP.Y(), aTrP.Z());
    chfi3d_tr("[CHFI3D]   isfirst=%s  spine status=%d  onsame=%s\n",
              isfirst ? "yes" : "no", (int)stat, onsame ? "YES" : "no");
  }
""")
        fe += n

    i = a.find("if (onsame) ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc == 1));", fs, fe)

    if trace:
        n = a.insert_before(i, r"""    if (chfi3d_trace_on()) {
      chfi3d_tr("[CHFI3D]   --- corner curve between fillet and face at end ---\n");
      chfi3d_tr("[CHFI3D]   onsame=%s IFadArc=%d IFopArc=%d inters=%s\n",
                onsame ? "YES" : "no", IFadArc, IFopArc, inters ? "yes" : "no");
      chfi3d_tr_surf("face at end (Bs)", Bs);
      chfi3d_tr("[CHFI3D]   BEFORE recale: pfac1=(%.9f, %.9f) pfac2=(%.9f, %.9f) du=%.9f\n",
                pfac1.X(), pfac1.Y(), pfac2.X(), pfac2.Y(), pfac2.X() - pfac1.X());
      {
        Handle(Geom_Surface) aTrS = Bs.ChangeSurface().Surface();
        Handle(Geom_RectangularTrimmedSurface) aTrT =
          Handle(Geom_RectangularTrimmedSurface)::DownCast(aTrS);
        if (!aTrT.IsNull()) aTrS = aTrT->BasisSurface();
        if (aTrS->IsUPeriodic()) {
          Standard_Real aPer = aTrS->UPeriod();
          Standard_Real aDu = fabs(pfac2.X() - pfac1.X());
          if (aDu > 0.5 * aPer)
            chfi3d_tr("[CHFI3D]   *** |du|=%.9f > half period %.9f : THE TWO POINTS SIT ON "
                      "OPPOSITE SIDES OF THE SEAM.%s ***\n", aDu, 0.5 * aPer,
                      onsame ? " ChFi3d_Recale will fix it."
                             : " onsame is FALSE so ChFi3d_Recale is SKIPPED.");
          else
            chfi3d_tr("[CHFI3D]   |du|=%.9f <= half period %.9f : no seam jump\n",
                      aDu, 0.5 * aPer);
        }
      }
    }
""")
        i += n
        fe += n

    if fix:
        # replace the guarded call with an unconditional one
        a.lines[i] = (
            "    // ------------------------------------------------------------------\n"
            "    // seam-fillet fix, 2026-09-12.\n"
            "    // pfac1 and pfac2 are two 2d points on the SAME face surface Bs. When that\n"
            "    // surface is periodic they can come out on opposite branches of u (u and\n"
            "    // u+2pi are the same 3d point, so no downstream check notices), and then\n"
            "    // Pardeb/Parfin describe the long way round the cylinder instead of the\n"
            "    // short arc. ChFi3d_Recale is the helper that normalises exactly this.\n"
            "    // It was called only in the `onsame` case; the seam defect happens with\n"
            "    // onsame == false, where it was skipped. IntersectMoreCorner (the sibling\n"
            "    // routine) already calls it unconditionally.\n"
            "    ChFi3d_Recale(Bs,pfac1,pfac2,%s);\n"
            "    // ------------------------------------------------------------------"
        ) % ("(IFadArc == 1)" if refon1 == "orig"
             else ("Standard_True" if refon1 else "Standard_False"))
        a.edits += 1

    if trace:
        n = a.insert_after(i, r"""    if (chfi3d_trace_on())
      chfi3d_tr("[CHFI3D]   AFTER  recale: pfac1=(%.9f, %.9f) pfac2=(%.9f, %.9f) du=%.9f\n",
                pfac1.X(), pfac1.Y(), pfac2.X(), pfac2.Y(), pfac2.X() - pfac1.X());
""")
        fe += n

        k = a.find("ChFi3d_Couture(Fv,couture,edgecouture);", fs, fe)
        n = a.insert_after(k, r"""    if (chfi3d_trace_on()) {
      chfi3d_tr("[CHFI3D]   corner curve built: param [%.9f, %.9f]\n", Udeb, Ufin);
      if (!Pc.IsNull()) {
        gp_Pnt2d aQ1 = Pc->Value(Udeb), aQ2 = Pc->Value(Ufin);
        chfi3d_tr("[CHFI3D]   its pcurve on the face at end: u %.9f -> %.9f (span %.9f)\n",
                  aQ1.X(), aQ2.X(), fabs(aQ2.X() - aQ1.X()));
      }
      chfi3d_tr("[CHFI3D]   ChFi3d_Couture: seam on face at end = %s\n",
                couture ? "YES" : "no");
    }
""")
        fe += n

    a.save()
    return a.edits


def status():
    for f in FILES:
        p = os.path.join(SRC, f)
        b = os.path.join(BACKUP, f)
        cur = open(p, "rb").read()
        base = open(b, "rb").read() if os.path.exists(b) else b""
        marks = []
        if b"chfi3d_trace_on" in cur:
            marks.append("TRACE")
        if b"seam-fillet fix" in cur:
            marks.append("FIX")
        print("  %-24s %8d bytes  %-8s  %s" % (
            f, len(cur), "PRISTINE" if cur == base else "MODIFIED",
            "+".join(marks) if marks else "-"))


def main():
    args = [a.lower() for a in sys.argv[1:]]
    if not args:
        raise SystemExit(__doc__)
    print("tree: %s" % SRC)
    if args[0] == "backup":
        do_backup("force" in args)
        status()
        return
    if args[0] == "status":
        status()
        return
    if args[0] == "revert":
        do_revert()
        status()
        return
    trace = "trace" in args
    fix = "fix" in args
    refon1 = "orig"
    if "true" in args:
        refon1 = True
    if "false" in args:
        refon1 = False
    if not (trace or fix):
        raise SystemExit("nothing to do: name `trace`, `fix`, or both")
    do_backup()
    do_revert()
    n1 = patch_builder(trace)
    n2 = patch_c1(trace, fix, refon1)
    print("applied: trace=%s fix=%s refon1=%s ; %d + %d edits"
          % (trace, fix, refon1 if fix else "-", n1, n2))
    status()


if __name__ == "__main__":
    main()
