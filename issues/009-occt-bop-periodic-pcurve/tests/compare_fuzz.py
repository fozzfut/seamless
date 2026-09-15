"""Compare two boolean_fuzz.py result files and judge every record in which the two kernels differ.

    <python> compare_fuzz.py <stock.jsonl> <patched.jsonl> [<report.txt>]
(any Python 3 - FreeCAD's own bin/python.exe does; the first file is taken as the stock kernel, the second as patched)

SAME   isValid, error, number of solids (Section: of edges) equal, and volume (Section: total edge length) within 1e-9
       relative. The runs are deterministic: one kernel gives bit-identical numbers on the same case.

Judging one record on one kernel, from that kernel's own numbers. WRONG, with the first reason that applies:
  error        the operation raised;
  validity     the result fails isValid() while the reference result passes;
  solids       (wide) another number of solids than the reference;
  consistency  (Cut, Common, Fuse) max(|cut + common - V(base)|, |V(base) + V(tool) - common - fuse|) / (V(base) + V(tool))
               above ID_TOL - V analytic for a random pair, the kernel's own volumes of base and widened tool for a wide one;
  deviation    (wide) |result - reference| above REF_REL * |reference| + ABS + K * strip, the reference being the same
               operation on the clean primitive in the same run, and strip = (over / 2 pi) * V(tool) the volume the
               widening adds to the tool (Section: 2 * over * r of length).
otherwise right; a Section of a random pair is 'undecided'.

The constants come from the regression run of 15 September 2026 (1752 records, README "Regression testing") and are
printed in the report:
  ID_TOL 1e-3     random pairs agree to a median 5.2e-8, 98 % below 8.6e-5 on both kernels; the two above are 0.038 and 0.36
  REF_REL 1e-4    the cylinder turned half a turn at exactly one period matches the clean one to 3.8e-10 mm3
  K 10            a widened cylinder on the patched kernel is off its reference by up to 7.54 strips
  B-spline tools  ID_TOL and REF_REL 1e-2: OCCT integrates B-spline volumes coarsely - consistency up to 0.0074 on both
                  kernels, 0.0046 at exactly one period; Part.makeCylinder(10, 30).toNurbs() reads 9505.976 for 9424.778
The patch passes when no record is right on the stock kernel and wrong on the patched one, and every record that differs
is wrong on the stock kernel or right on both.
"""
import json
import math
import sys

ID_TOL = 1e-3
REF_REL = 1e-4
BSPLINE_TOL = 1e-2
K = 10.0
ABS = 1e-3


def load(path):
    header, records = None, {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("header"):
                header = obj
            elif obj.get("footer"):
                header["seconds"] = obj["seconds"]
            else:
                records[obj["id"]] = obj
    return header, records


def value(result):
    if "error" in result:
        return None
    return result.get("length") if "length" in result else result.get("volume")


def same(a, b):
    ra, rb = a.get("result", {}), b.get("result", {})
    if ("error" in ra) != ("error" in rb) or ra.get("valid") != rb.get("valid"):
        return False
    if ra.get("solids") != rb.get("solids") or ra.get("edges") != rb.get("edges"):
        return False
    va, vb = value(ra), value(rb)
    if va is None or vb is None:
        return va is vb
    return abs(va - vb) <= 1e-9 * max(1.0, abs(va), abs(vb))


def show(result):
    if "error" in result:
        return "error %s" % result["error"]
    if "length" in result:
        return "valid %s, %d edges, length %.6f" % (result.get("valid"), result.get("edges"), result["length"])
    return "valid %s, %d solids, %.6f" % (result.get("valid"), result.get("solids"), result["volume"])


def consistency(rec, records, vb, vt):
    """(relative error or None, detail) of the inclusion-exclusion of the record's pair on one kernel."""
    stem = rec["id"].rsplit("-", 1)[0]
    ops = {op: records.get("%s-%s" % (stem, op), {}).get("result", {}) for op in ("cut", "common", "fuse")}
    vals = {op: value(r) for op, r in ops.items()}
    if any(v is None for v in vals.values()):
        return None, "an operation of the pair raised"
    e1 = abs(vals["cut"] + vals["common"] - vb)
    e2 = abs(vb + vt - vals["common"] - vals["fuse"])
    rel = max(e1, e2) / max(abs(vb) + abs(vt), 1.0)
    return rel, "|cut+common-Vb| %.6g, |Vb+Vt-common-fuse| %.6g (%.2g)" % (e1, e2, rel)


def judge(rec, records):
    """(verdict, reason, detail, relative deviation from the reference or None)."""
    res = rec.get("result")
    if res is None or "error" in res:
        return "WRONG", "error", (show(res) if res else rec.get("error", "")[-200:]), None
    if rec["family"] == "random":
        if rec["op"] == "section":
            return "undecided", "", "section of a random pair: %s" % show(res), None
        rel, d = consistency(rec, records, rec["base"]["volume"], rec["tool"]["volume"])
        if rel is None:
            return "WRONG", "error", d, None
        if rel > ID_TOL:
            return "WRONG", "consistency", "%s; pair %s" % (show(res), d), None
        return "right", "", "%s; pair %s" % (show(res), d), None
    tool = rec["tool"]
    tol = BSPLINE_TOL if tool["kind"] == "bspline" else None
    ref = rec["reference"]
    v, w = value(res), value(ref)
    if w is None:
        return "undecided", "", "%s; the reference raised %s" % (show(res), ref.get("error")), None
    dev = abs(v - w)
    rel_dev = dev / max(abs(w), 1.0)
    if rec["op"] == "section":
        slack = 2.0 * tool["over"] * tool["params"][0]
        allowed = (tol or 1e-3) * abs(w) + ABS + K * slack
    else:
        slack = tool["over"] / (2 * math.pi) * abs(rec["tool_volume"])
        allowed = (tol or REF_REL) * abs(w) + ABS + K * slack
    detail = "%s; reference %s; off %.6g (%.2g relative, allowed %.3g)" % (show(res), show(ref), dev, rel_dev, allowed)
    if not res.get("valid") and ref.get("valid"):
        return "WRONG", "validity", detail, rel_dev
    if rec["op"] != "section":
        if res.get("solids") != ref.get("solids"):
            return "WRONG", "solids", detail, rel_dev
        rel, d = consistency(rec, records, rec["base_volume"], rec["tool_volume"])
        detail += "; pair %s" % d
        if rel is None or rel > (tol or ID_TOL):
            return "WRONG", "consistency", detail, rel_dev
    if dev > allowed:
        return "WRONG", "deviation", detail, rel_dev
    return "right", "", detail, rel_dev


def main(argv):
    stock_path, patched_path = argv[1], argv[2]
    out = open(argv[3], "w", encoding="utf-8") if len(argv) > 3 else None

    def say(line=""):
        print(line)
        if out:
            out.write(line + "\n")

    hs, stock = load(stock_path)
    hp, patched = load(patched_path)
    say("stock   %s  TKBO %s  %d records  %s s" % (hs["exe"], hs["tkbo_md5"], len(stock), hs.get("seconds")))
    say("patched %s  TKBO %s  %d records  %s s" % (hp["exe"], hp["tkbo_md5"], len(patched), hp.get("seconds")))
    say("ID_TOL %g, REF_REL %g, K %g, B-spline %g, ABS %g" % (ID_TOL, REF_REL, K, BSPLINE_TOL, ABS))
    ids = sorted(set(stock) | set(patched))
    missing = [i for i in ids if i not in stock or i not in patched]
    differ = [i for i in ids if i in stock and i in patched and not same(stock[i], patched[i])]
    families = {}
    for i in ids:
        rec = stock.get(i) or patched.get(i)
        key = rec.get("family", "?") if rec.get("family") != "wide" else "wide %s" % rec.get("tool", {}).get("kind", "?")
        families[key] = families.get(key, 0) + 1
    say("records %d %s; in one file only %d, identical %d, different %d" % (
        len(ids), families, len(missing), len(ids) - len(missing) - len(differ), len(differ)))
    for i in missing:
        say("  only in %s: %s" % ("stock" if i in stock else "patched", i))

    verdicts = {}
    for name, recs in (("stock", stock), ("patched", patched)):
        verdicts[name] = {i: judge(recs[i], recs) for i in ids if i in recs}
        counts = {}
        for j, why, _d, _r in verdicts[name].values():
            key = j if j != "WRONG" else "WRONG %s" % why
            counts[key] = counts.get(key, 0) + 1
        say("%-7s all records: %s" % (name, dict(sorted(counts.items()))))

    classes = {}
    for i in differ:
        js, ws, ds, rs = verdicts["stock"][i]
        jp, wp, dp, rp = verdicts["patched"][i]
        key = "stock %s, patched %s" % ("%s (%s)" % (js, ws) if ws else js, "%s (%s)" % (jp, wp) if wp else jp)
        classes.setdefault(key, []).append((i, ds, dp, rs, rp))
    say()
    say("DIFFERENT records by verdict:")
    for key in sorted(classes):
        rows = classes[key]
        rs = [r[3] for r in rows if r[3] is not None]
        rp = [r[4] for r in rows if r[4] is not None]
        kinds = {}
        for r in rows:
            rec = stock[r[0]]
            k = "%s %s %s" % (rec.get("tool", {}).get("kind", rec["family"]), rec["op"], rec.get("base", {}).get("turn", ""))
            kinds[k] = kinds.get(k, 0) + 1
        say("  %-52s %4d  stock off the reference %s, patched %s; %s" % (
            key, len(rows), ("%.3g..%.3g" % (min(rs), max(rs))) if rs else "-",
            ("%.3g..%.3g" % (min(rp), max(rp))) if rp else "-", dict(sorted(kinds.items()))))
    for key in sorted(classes):
        say()
        say("DIFFERENT - %s: %d" % (key, len(classes[key])))
        for i, ds, dp, _rs, _rp in classes[key]:
            rec = stock[i]
            width = rec.get("tool", {}).get("width_over_period")
            turn = rec.get("base", {}).get("turn")
            say("  %s%s%s" % (i, "" if width is None else "  (face wider than its period by %.3g)" % width,
                              "" if turn is None else ", base turned %s" % turn))
            say("      stock:   %s" % ds)
            say("      patched: %s" % dp)
    same_wrong = [(i, verdicts["stock"][i]) for i in ids
                  if i not in differ and i not in missing and verdicts["stock"][i][0] == "WRONG"]
    say()
    groups = {}
    for i, (_j, why, _d, _r) in same_wrong:
        rec = stock[i]
        k = "%s %s, %s" % (rec.get("tool", {}).get("kind", rec["family"]), rec["op"], why)
        groups[k] = groups.get(k, 0) + 1
    say("IDENTICAL on both kernels and judged WRONG on both (not the patch's doing): %d %s" % (
        len(same_wrong), dict(sorted(groups.items()))))
    for i, (_j, why, d, _r) in same_wrong:
        say("  %s [%s]: %s" % (i, why, d))
    broke = [c for k, v in classes.items() if k.startswith("stock right") and "patched WRONG" in k for c in v]
    unexplained = [c for k, v in classes.items() if not k.startswith("stock WRONG") and k != "stock right, patched right"
                   for c in v]
    say()
    say("FUZZ-VERDICT: %s (different records: %d; right on stock and wrong on patched: %d; different and neither wrong "
        "on stock nor right on both: %d; missing: %d)" % (
            "PASS" if not broke and not unexplained and not missing else "FAIL", len(differ), len(broke),
            len(unexplained), len(missing)))
    if out:
        out.close()


if __name__ == "__main__":
    main(sys.argv)
