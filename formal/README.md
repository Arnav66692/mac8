# Formal proof of the strobe handshake

Round three gate. The async latency dimension, each synchronized edge
resolving in 2 or 3 clocks independently, verified over all traces, not
spot checked. F2, F3, and the reset release all lived in this dimension.

## The model

f_handshake.sv. A constrained driver produces every legal strobe per spec
v0.4, free choices decide when it rises and falls. On every transition
cycle the value ff1 samples is a free choice, the metastable resolution
direction, rises and falls both. The real mac8_sync and mac8_ctrl RTL sit
under test unmodified. cmd is a free input, so the properties hold for
every command, not only MAC. Properties are safety form.

- P1. Never more than one rise in flight.
- P2. No accept without a pending rise, kills doubles and phantoms.
- P3. A rise never finds the previous one unconsumed, kills losses, the
  lockout never eats a legal command at any latency combination and any
  legal spacing.
- P4. Busy never blocks a legal accept. cmd is free, and MAC is the only
  command that raises busy, so the free proof subsumes the worst case.

## The assertion window and the bounded response

The window opens at rst_n deassert, so the properties hold from the first
cycle the design is live, including the arm transient right after reset
release. An earlier version gated the assertions at a fixed boot cycle
past the first rise, which left the release edge unwatched, round four
closed that.

The strengthening invariant, pending implies since_rise at most three, is
a bounded response property, not just a helper for induction. It says an
outstanding obligation is always young, an accept lands within three
clocks of its rise. A lost command holds pending at 1 while since_rise
climbs, so it trips the invariant at since_rise four, three clocks after
the rise, with no next rise required. The proof does not need a second
rise to prove the first one is never dropped.

The obligation counter is a free standing harness signal, never DUT logic.
It saturates, it does not wrap, and three sticky flags latch any phantom,
double, or busy block forever. So a violation in any cycle is a permanent
trace, and neither modular arithmetic nor an arbitrary induction start
state can launder it away.

## How to run

```
brew install yosys z3

yosys -q -p "
read_verilog -formal -sv formal/f_handshake.sv src/mac8_sync.sv src/mac8_ctrl.sv
prep -top f_handshake
flatten
async2sync
opt_clean
write_smt2 -wires formal/build/f_handshake.smt2
"
yosys-smtbmc -s z3 -t 60 formal/build/f_handshake.smt2   # BMC base
yosys-smtbmc -s z3 -i -t 30 formal/build/f_handshake.smt2  # induction
```

## Result, 2026-07-15

Yosys 0.67, yosys-smtbmc, z3. BMC to depth 60, PASSED. Temporal induction
successful at step 23, the proof is unbounded. The induction depth grew
from 13 to 23 when the sticky flags and the free cmd enlarged the state,
still a full unbounded proof. Vacuity checked, an added assert that no
accept ever happens fails in BMC as it must, so the model produces real
handshakes and the proof is not vacuous.

Coverage witness, round four. A phantom accept forced at boot 7, inside
the window the old proof did not watch, is now caught at boot 7 by the no
accept without a pending rise assertion. That is the release adjacent
region where F2 lived, now observed from the first live cycle.

The concrete enumeration of the same dimension is test_latency_grid in
tb/test_top.py, 24 cells, spacings 4, 5, 6, all latency combinations, both
alignments, every cell matching prediction. Spacing 4 is below the
contract and resolution dependent by design, slow then fast blocks, the
rest pass, spec v0.4 states that row as best effort.
