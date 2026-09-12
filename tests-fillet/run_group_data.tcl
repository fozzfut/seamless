# Runner for one OCCT test group with the real test-data repository attached.
# testgrid gives every case its own DRAWEXE process; each group's "begin" sets
# cpulimit, so a hung fillet is killed and recorded instead of stopping the run.
set grp    $env(SEAMLESS_GROUP)
set outdir $env(SEAMLESS_OUTDIR)
set par    $env(SEAMLESS_PARALLEL)
pload TOPTEST
testgrid -outdir $outdir -overwrite -parallel $par $grp
exit 0
