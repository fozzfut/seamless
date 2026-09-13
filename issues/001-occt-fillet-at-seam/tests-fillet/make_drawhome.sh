#!/bin/bash
# make_drawhome.sh <occt-src> <dest>
#
# Builds a private DRAWHOME: a copy of OCCT's src/DrawResources in which
# "checkview" is replaced by a no-op.
#
# WHY: testgrid runs every case in its own DRAWEXE child process
# ("exec <<{} DRAWEXE -f ..." in TestCommands.tcl), so a proc redefined in the
# parent does not reach the cases -- the override has to live in the resource
# files the children load, which they find through $DRAWHOME.
#
# WHAT checkview DOES: it opens a Draw view and calls "xwd" to save a PNG for
# the HTML report. This build has no viewer (Visualization is not built, DRAWEXE
# runs with -b, and the machine must stay unattended), so xwd fails with
# "cannot create WIC File Stream" and turns every otherwise-passing case into
# FAILED. The snapshot carries no geometry, so removing it loses no signal.
# The same no-op is used for the stock run and the patched run.
set -eu
SRC="${1:?usage: make_drawhome.sh <occt-src> <dest>}"
DST="${2:?usage: make_drawhome.sh <occt-src> <dest>}"
[ -f "$SRC/src/DrawResources/CheckCommands.tcl" ] || { echo "no DrawResources under $SRC" >&2; exit 2; }
rm -rf "$DST"
cp -r "$SRC/src/DrawResources" "$DST"
cat >> "$DST/CheckCommands.tcl" <<'TCL'

# seamless project: no viewer in this build -- see make_drawhome.sh
proc checkview {args} {
    puts "checkview: skipped (no viewer in this build)"
    return
}
TCL
echo "private DRAWHOME ready: $DST"
