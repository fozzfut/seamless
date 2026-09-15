"""Compare FreeCAD's own test suites between two run_regression.ps1 output folders.

    <python> compare_suites.py <stock out> <patched out> [<report.txt>]

Reads suite-<name>.out.txt and .err.txt found anywhere under each folder. Compared per suite, from what unittest itself
prints and nothing guessed: the "Ran N tests" line, the closing "OK (...)" / "FAILED (...)" line, and the names of the
failing and erroring tests from their "FAIL: ..." / "ERROR: ..." headers. (A per-line "name ... ok" parse is not used:
measured on TestCAMApp, output the tests print lands between the name and its status, and such a parse lost 258 of 731
tests and reported two differences that were not there.)
"""
import glob
import os
import re
import sys

RAN = re.compile(r"^Ran (\d+) tests? in [\d.]+s")
END = re.compile(r"^(OK|FAILED)(\s*\(.*\))?\s*$")
HEAD = re.compile(r"^(FAIL|ERROR): (.+?)\s*$")


def parse(folder, suite):
    text = ""
    for ext in ("out", "err"):
        for path in sorted(glob.glob(os.path.join(folder, "**", "suite-%s.%s.txt" % (suite, ext)), recursive=True)):
            with open(path, encoding="utf-8", errors="replace") as f:
                text += f.read() + "\n"
    ran, end, failing = None, None, set()
    for line in text.splitlines():
        r = RAN.match(line)
        if r:
            ran = int(r.group(1))
        e = END.match(line.strip())
        if e:
            end = line.strip()
        h = HEAD.match(line)
        if h:
            failing.add("%s: %s" % (h.group(1), h.group(2)))
    return ran, end, failing


def main(argv):
    stock, patched = argv[1], argv[2]
    out = open(argv[3], "w", encoding="utf-8") if len(argv) > 3 else None

    def say(line=""):
        print(line)
        if out:
            out.write(line + "\n")

    suites = sorted(set(os.path.basename(p)[6:-8] for folder in (stock, patched)
                        for p in glob.glob(os.path.join(folder, "**", "suite-*.out.txt"), recursive=True)))
    if not suites:
        say("SUITES-VERDICT: NOTHING TO COMPARE (no suite-*.out.txt under %s or %s)" % (stock, patched))
        return
    different = 0
    for suite in suites:
        rs, es, fs = parse(stock, suite)
        rp, ep, fp = parse(patched, suite)
        same = rs == rp and es == ep and fs == fp and rs is not None
        different += 0 if same else 1
        say("%s: %s" % (suite, "same" if same else "DIFFERENT"))
        say("  stock:   Ran %s | %s | %d failing" % (rs, es, len(fs)))
        say("  patched: Ran %s | %s | %d failing" % (rp, ep, len(fp)))
        for name in sorted(fs | fp):
            where = "both" if name in fs and name in fp else ("stock only" if name in fs else "patched only")
            say("    %s  [%s]" % (name, where))
    say()
    say("SUITES-VERDICT: %s (%d of %d suite(s) differ)" % ("SAME" if different == 0 else "DIFFERENT", different, len(suites)))
    if out:
        out.close()


if __name__ == "__main__":
    main(sys.argv)
