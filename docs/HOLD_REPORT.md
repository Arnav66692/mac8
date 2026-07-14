# Hold report, per corner

From the hardened run on main, CI run 29314372443, sky130A, nine corners. Setup at 50 MHz on this design is free. Hold is where hardened tiles die, so it gets its own table.

Positive slack is met. Hold worst slack is the number that matters.

| Corner | Hold WNS ns | Hold TNS ns | Setup WNS ns |
|---|---|---|---|
| nom_tt_025C_1v80 | plus 0.3391 | 0 | plus 10.06 |
| min_tt_025C_1v80 | plus 0.3359 | 0 | plus 10.23 |
| max_tt_025C_1v80 | plus 0.3419 | 0 | plus 9.914 |
| nom_ss_100C_1v60 | plus 0.9628 | 0 | plus 0.967 |
| min_ss_100C_1v60 | plus 0.9475 | 0 | plus 1.256 |
| max_ss_100C_1v60 | plus 0.9677 | 0 | plus 0.695 |
| nom_ff_n40C_1v95 | plus 0.1133 | 0 | plus 13.24 |
| min_ff_n40C_1v95 | plus 0.1107 | 0 | plus 13.30 |
| max_ff_n40C_1v95 | plus 0.1162 | 0 | plus 13.18 |

## The worst number, plainly

Worst hold slack is plus 0.111 ns, at min_ff_n40C_1v95, the fast corner. Hold is tightest at the fast corner because fast silicon shortens data paths toward the capture edge. It is met, with 0.111 ns to spare. Hold TNS is zero at every corner, no path fails.

Hold is met but the fast corner margin is thin. The flow already spent hold buffers to get here, 12 hold buffers in the netlist. This is the number to watch if the design or the floorplan changes.
