---
tags: [chip-track, signoff]
project: P1
status: timing annotated gate level pass recorded
---

# Timing annotated gate level result

Round three item 8, recorded here so the result lives in the package, not
only in a log summary.

## What ran

The nine test pin only suite, test/test.py, on the powered gate level
netlist of the final hardened run, with a standard delay file back
annotated so the sim carries real cell and interconnect delays, not unit
delays. Tooling, test/Makefile.sdf and test/sdf_annotate.v, Icarus with
gspecify, the sky130 timing models.

## Corner

max_ss_100C_1v60, the slow signoff corner, the SDF is
tt_um_arnav_mac8__max_ss_100C_1v60.sdf from CI run 29401092054, commit
49f5f29, netlist sha256
5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0.

## Result

Pass. All 9 pin tests pass with timing annotation at max_ss_100C_1v60,
matching the unit delay CI result. The annotation was confirmed applied,
not silently skipped, by the missing file probe, Icarus warns loudly when
a named SDF cannot be opened and stayed silent on this one.

The run covers the power up X window. Every gate level flop starts X. The
reset is synchronous, an AND into each flop D, so every reset controlled
flop clears on the one clock edge where rst_n is sampled low, together,
not staggered. The two reset synchronizer flops, rst_ff1 and rst_ff2, have
no reset of their own and settle to the pad value within 2 clocks. The
reset state and reset release tests, test_reset_pin_state and
test_reset_release_strobe_high_gl, pass through that window with annotated
timing, so the design reaches a clean reset state and no X survives into
the first command. This is the annotated confirmation of the same X window
the CI run covers with unit delays.
