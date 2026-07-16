# Hold report, per corner

From the final hardened run on main, CI run 29401092054, commit 49f5f29, sky130A, nine corners. Final netlist sha256 5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0, the same netlist behind every table in docs/CDC_MTBF.md, one run feeds the whole package. Setup at 50 MHz on this design is free. Hold is where hardened tiles die, so it gets its own table.

Positive slack is met. Hold worst slack is the number that matters.

| Corner | Hold WNS ns | Hold TNS ns | Setup WNS ns |
|---|---|---|---|
| nom_tt_025C_1v80 | plus 0.3387 | 0 | plus 10.56 |
| min_tt_025C_1v80 | plus 0.3359 | 0 | plus 10.69 |
| max_tt_025C_1v80 | plus 0.3404 | 0 | plus 10.44 |
| nom_ss_100C_1v60 | plus 0.9529 | 0 | plus 1.774 |
| min_ss_100C_1v60 | plus 0.9459 | 0 | plus 2.011 |
| max_ss_100C_1v60 | plus 0.9598 | 0 | plus 1.556 |
| nom_ff_n40C_1v95 | plus 0.1125 | 0 | plus 13.32 |
| min_ff_n40C_1v95 | plus 0.1106 | 0 | plus 13.38 |
| max_ff_n40C_1v95 | plus 0.1137 | 0 | plus 13.27 |

## The worst number, plainly

Worst hold slack is plus 0.111 ns, at min_ff_n40C_1v95, the fast corner. That number is net of margin, the hold required time already includes the 0.25 ns clock uncertainty and the flow applies a 5 percent timing derate, visible in the corner's min.rpt and sta.log. Hold is tightest at the fast corner because fast silicon shortens data paths toward the capture edge. It is met, with 0.111 ns to spare after those margins. Hold TNS is zero at every corner, no path fails.

Hold is met but the fast corner margin is thin. The flow spent 19 hold buffers in this netlist to get here, up from 12 before the round two RTL changes. This is the number to watch if the design or the floorplan changes.

## Open warts, same run

Max slew violations, 254 at max_ss, 33 at max_tt, worst 1.207 ns against the 0.750 ns pin limit at max_ss. Zero at ff, zero fanout violations. Setup and hold are met everywhere, the slew stays a signoff wart, the real fix is resizer repair at the slow corner, a PPA call deferred at round two. The tt slew counts are new against the pre round two baseline, which was ss only, same class, same deferral.
