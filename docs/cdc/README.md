# Metastability extraction bench

The bench for the synchronizer first flop, ff1. It is the setup for the MTBF
work. The tau and T0 fit, the resolution plot, and the MTBF paragraph are
Arnav's, this directory only provides the bench and a sanity run.

## The cell

ff1 in the hardened netlist maps to sky130_fd_sc_hd__dfxtp_2, item 1 of the
round 1.5 review. A plain flop, since the reset is synchronous and folds into
the D logic. The bench characterizes that exact cell.

## Structure, after Beer and Ginosar

A fixed clock rising edge. The D rising edge time is the swept parameter. As
the D edge approaches the clock, the flop is driven toward its capture balance
point, the D edge time where the outcome flips between capturing 0 and 1. The
bench locates that balance and logs the Q resolution time against the offset
from it.

Efficiency note. The device models parse once per session. A control loop then
reruns the transient for each D edge time with alterparam and reset, so the
cost is one parse plus many fast sims, not one parse per point. This matters,
one parse is about 40 seconds, a sim is under a second.

## How to run

```
# Extract the cell subckt once, from the PDK combined cell library.
CELL=~/.volare/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice
awk '/^\.subckt sky130_fd_sc_hd__dfxtp_2 /{f=1} f{print} /^\.ends/{if(f)exit}' \
  "$CELL" > dfxtp_2.spice

# Coarse sanity sweep at tt, one session.
export CELL_SPICE=$PWD/dfxtp_2.spice
export BAL_CENTER=20e-9 BAL_STEP=1e-12 BAL_NPTS=140
python3 meta_bench.py tt > sweep_tt.csv

# To zoom on the balance for the fine resolution tail, narrow the window.
export BAL_CENTER=19.9765e-9 BAL_STEP=5e-15 BAL_NPTS=200
python3 meta_bench.py tt > zoom_tt.csv
```

Corners are tt at 1.80 V 25 C and ss at 1.60 V 100 C, pass the corner as the
argument. The PDK comes from volare.

## Refined bench, round 1.5 item 4

meta_bench.py now probes the master latch storage node, xdut.a_466_413#, not
Q. The master cross coupled pair is a_466_413# and a_634_159#. The input
transmission gate writes a_466_413# while CLK is low and the clocked feedback
inverter holds it after the rising edge, so the metastable dwell lives there.
Q sits behind the slave tgate, an inverter, and the output buffer, which
regenerate and hide the dwell. That is why the first sweep read flat.

A grid ladder locates the balance to sub femtosecond, four levels, 2 ps down
to 0.25 fs steps. Then log spaced offsets on both sides, 1 fs to 1 ps, measure
the resolution time, the last time the master node sits inside the 0.3 to 0.7
vdd band after the clock edge. Tolerances reltol 1e-6, abstol 1e-15, gear
integration, max step 0.5 ps, single session per grid.

Results, committed with the measurement deck hash in the filename.

- sweep_tt_94ab4266.csv, tt 1.80 V 25 C, balance at 4.976707125 ns against a
  5 ns clock edge. Resolution 0.106 ns at 1000 fs, 0.467 ns at 1 fs.
- sweep_ss_2160e2ac.csv, ss 1.60 V 100 C, balance from its own ladder.
  Resolution 0.270 ns at 1000 fs, 1.364 ns at 1 fs.
- balance_tt.log and balance_ss.log, the ladder convergence records.

Both corners pass the sanity band, resolution grows as offset shrinks and is
roughly linear against log offset, about 0.10 ns per decade at tt and about
0.29 ns per decade at ss. The tau and T0 fit, the plot, and all MTBF text are
Arnav's, this directory stops at the CSVs.

## First sanity run result, Q probe, tt, raw, superseded

sweep_tt_sanity.csv, 141 points, one session, about 95 seconds. Balance found
at td 19.9765 ns. The capture flips cleanly there.

| offset from balance ps | final Q | resolution ns |
|---|---|---|
| minus 2.5 | 1.0 | 0.0 |
| minus 1.5 | 1.0 | 0.0 |
| minus 0.5 | 1.0 | 0.0 |
| plus 0.5 | 0.0 | 0.0 |
| plus 1.5 | 0.0 | 0.0 |
| plus 2.5 | 0.0 | 0.0 |

What this proves. The bench converges, the search lands on the balance point
and the captured value flips there, 1 for a D edge before the balance, 0 after.

What this does not yet show. The resolution time reads at the floor across the
plus and minus picosecond offsets, so the metastable window at tt is under 1
picosecond at this sweep precision. Exposing the resolution tail, where Q
lingers near mid rail for tens of picoseconds, needs a femtosecond zoom and
tighter solver handling. That fine curve and the tau fit are the next step,
Arnav's, this bench is the framework and the located balance point.
