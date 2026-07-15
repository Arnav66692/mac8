# Formal proof of the strobe handshake

Round three gate. The async latency dimension, each synchronized edge
resolving in 2 or 3 clocks independently, verified over all traces, not
spot checked. F2, F3, and the reset release all lived in this dimension.

## The model

f_handshake.sv. A constrained driver produces every legal strobe per spec
v0.4, free choices decide when it rises and falls. On every transition
cycle the value ff1 samples is a free choice, the metastable resolution
direction, rises and falls both. The real mac8_sync and mac8_ctrl RTL sit
under test unmodified, cmd held at MAC. Properties are safety form.

- P1. Never more than one rise in flight.
- P2. No accept without a pending rise, kills doubles and phantoms.
- P3. A rise never finds the previous one unconsumed, kills losses, the
  lockout never eats a legal command at any latency combination and any
  legal spacing.
- P4. Busy never blocks a legal accept.

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
successful at step 13, the proof is unbounded. Vacuity checked, an added
assert that no accept ever happens fails in BMC as it must, so the model
produces real handshakes and the proof is not vacuous.

The concrete enumeration of the same dimension is test_latency_grid in
tb/test_top.py, 24 cells, spacings 4, 5, 6, all latency combinations, both
alignments, every cell matching prediction. Spacing 4 is below the
contract and resolution dependent by design, slow then fast blocks, the
rest pass, spec v0.4 states that row as best effort.
