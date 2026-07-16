# Formal proof of the strobe handshake

The handshake properties hold under exercised arm transient and ring
stimulus, verified by mutation. What that means honestly is below, because
this proof was vacuous twice before it was real.

## What the proof covers, and how it earned the claim

Rounds three and four proved the handshake and claimed to close the class
that produced F2, the arm bit, and F3, the lockout. An adversarial audit of
the proof itself then showed that claim was false. Deleting the arm bit
passed, deleting the lockout passed, because the driver held the strobe low
across reset release so the arm bit never saw an edge, and modeled one
synchronized edge per rise so the lockout never saw a ring. The properties
were watched but never stimulated, proven vacuously. Round five fixes the
stimulus, and the acceptance is not a green pass, it is the mutation gate,
each protection deleted from the RTL must make the proof fail.

## The model

f_handshake.sv. A constrained driver produces the legal strobe per spec
v0.4. A command edge carries free metastable latency, the value ff1 samples
on that edge is a free choice, so ff2 sees it in 2 or 3 clocks, the round
three dimension, retained. Three stimulus additions make the two
mechanisms reachable. The strobe can be held high across reset release,
force_high, the case the arm bit swallows. A command pulse can ring, a
clean deterministic dip inside its high pulse, a second threshold crossing,
the case the lockout suppresses. The first legal command lands at the
internal 3 clock hard floor, so an arm settle regression drops it. The real
mac8_sync and mac8_ctrl RTL sit under test unmodified. cmd is a free input,
so the properties hold for every command. Properties are safety form.

- P1. Never more than one command in flight.
- P2. No accept without a pending command, kills doubles and phantoms. A
  strobe high across reset and a ring both trip this if their protection is
  gone.
- P3. A command rise never finds the previous one unconsumed, kills losses.
- P4. Busy never blocks a legal accept. cmd is free, and MAC is the only
  command that raises busy, so the free proof subsumes the worst case.

Obligations are counted from command rises only, classified by spacing, a
physical rise closer than the legal 5 clocks is a ring, not a command, so
the harness never counts the ring's own extra edge as a second obligation.
The harness rst_n is the reset the core sees after mac8_rst_sync. That
module only delays release by two clean clocks, so gating the first rise at
the internal 3 clock floor covers the release window without instantiating
it.

## The mutation gate, the acceptance test

formal/mutation_test.sh. Base must pass, and every mutation that removes a
real protection must be caught, while a control that removes the edge detect
stays caught, proving the harness is live.

| Case | Mutation | Expected |
|---|---|---|
| base | none | PASS |
| M1 | delete the armed gate, accept_raw = ff2 and not ff3 | FAIL |
| M2 | delete the lockout, accept = accept_raw | FAIL |
| M3 | arm settle regressed 4 clocks | FAIL |
| control | delete the edge detect, accept_raw = ff2 and armed | FAIL |

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
yosys-smtbmc -s z3 -t 60 formal/build/base.smt2      # BMC base
yosys-smtbmc -s z3 -i -t 40 formal/build/base.smt2   # induction
bash formal/mutation_test.sh 60                       # the gate
```

## Result, 2026-07-16

Yosys 0.67, yosys-smtbmc, z3 4.16.0. Base, BMC to depth 60 PASSED, temporal
induction closed at step 30, the proof is unbounded. Vacuity checked, an
added assert that no accept ever happens fails in BMC as it must, so the
model produces real handshakes.

The mutation gate held. base PASS, M1 delete armed FAIL, M2 delete lockout
FAIL, M3 arm regression FAIL, control FAIL. Each mutation fails for its own
mechanism, verified by trace. M1 fails on P2 at step 7, a phantom accept
from a strobe held high across reset, measured from the smtbmc output. M2 fails on P2 at step 14, a double
accept from a ring. M3 fails on P3 and the bounded response at step 13, a
lost first command. This is the difference between a proof that passes and
a proof that proves something. The first two rounds passed and proved
nothing about the arm bit or the lockout.

The concrete enumeration of the latency dimension is test_latency_grid in
tb/test_top.py, 24 cells, spacings 4, 5, 6, all latency combinations, both
alignments, every cell matching prediction. Spacing 4 is below the
contract and resolution dependent by design, slow then fast blocks, the
rest pass, spec v0.4 states that row as best effort.
