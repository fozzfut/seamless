# The one configuration the narrowed guard does not separate by direction:
# a face CLOSED in U (so the new term is true) whose basis is ALSO periodic in V
# while the face is NOT closed in V.  ptorus R r v1 v2 gives exactly that: the
# tube is cut to 270 degrees in V, the revolution stays a full turn in U.
# If ChFi3d_Recale misfires in V, this is where it would show.
pload TOPTEST
foreach v2 {270 200 190 300} {
  foreach r {1 2 4} {
    catch {ptorus t 50 10 0 $v2} m1
    explode t E
    set n 0
    foreach e [directory t_*] { incr n }
    puts "TORUS v2=$v2 radius=$r edges=$n"
    for {set i 1} {$i <= $n} {incr i} {
      set st [catch {blend result t $r t_$i} msg]
      if {$st != 0} { puts "  edge $i : EXCEPTION $msg" ; continue }
      set chk [catch {checkshape result} cmsg]
      set vol "n/a"
      catch {
        set p [vprops result]
        regexp {Mass +: +([-0-9.e+]+)} $p all vol
      }
      puts "  edge $i : check=[string trim $cmsg] vol=$vol"
    }
  }
}
puts "TORUS_V_DONE"
exit 0
