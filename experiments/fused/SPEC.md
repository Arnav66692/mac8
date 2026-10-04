# MAC8 fused protocol candidate v1

Experimental implementation. Not a submitted chip revision. Baseline is
commit 7601c8d and its frozen interface remains docs/SPEC.md v0.5.

The pin map, signed arithmetic, saturation, registered byte readout,
reset crossing, command setup and hold, and five-clock read floor match
the baseline. All baseline commands except opcode 000 retain their meaning.

Opcode 000 is LDB_MAC. On an accepted command, latch ui_in into operand B
and schedule one MAC for the following core clock. That MAC consumes the
new B and existing A. This differs from baseline NOP and requires an
explicit fused=True driver. There is no runtime protocol autodetection.

The pending bit holds busy high while the delayed MAC is scheduled. Busy
also covers the cycle following MAC execution, as in the baseline. A
command arriving while busy is high is dropped. Five-clock rise spacing
remains sufficient because execution finishes before the next legal
accept, even with independent two or three clock synchronizer latencies.

Synchronized reset clears pending and cancels its execution if reset is
active at that execution edge. An accepted fused command can execute before
a later pad reset crosses the synchronizer. Reset then clears all data.
CLR follows the usual busy/drop rule, and clears accumulator and overflow
when accepted. The driver does not issue commands during the busy window.

The reused datapath receives only one control pulse per cycle. B load and
MAC deliberately occur on different clocks, avoiding old-B multiplication
and preserving the existing pulse-overlap guard.

Measure command cycles with the executable driver. Report synthesis
estimates separately from routed area and timing. No post-route or silicon
performance claim follows from this prototype.
