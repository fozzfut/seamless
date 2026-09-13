# Regression runner for the "seamless" project (OCCT ChFi3d_Recale patch).
#
# NOTE: testgrid runs every case in its OWN DRAWEXE process
# ("exec <<{} DRAWEXE -f ..." in TestCommands.tcl), so a proc defined here
# would NOT reach the cases.  The checkview no-op is therefore injected through
# a private DRAWHOME (see run_suite.sh and DrawResources/CheckCommands.tcl),
# which the child processes inherit.
#
# The per-case process isolation is also what bounds a hanging fillet: the
# group's "begin" sets cpulimit 600, enforced inside each child.

set grp    $env(SEAMLESS_GROUP)
set outdir $env(SEAMLESS_OUTDIR)

pload TOPTEST
testgrid -outdir $outdir -overwrite -parallel 0 $grp
exit 0
