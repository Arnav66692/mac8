# MAC8

An int8 serial multiply accumulate unit for the Tiny Tapeout TTSKY26c
shuttle, sky130. 8 bit signed times 8 bit signed, accumulated into 24 bit
signed with saturation and a sticky overflow flag. One multiplier, one
accumulator, one command decoder. The atom of AI compute, small enough to
tape out, deep enough to defend line by line.

Built RTL to GDS on open tools, SystemVerilog, cocotb, Icarus, Verilator,
LibreLane through the Tiny Tapeout flow. Every number below comes from a
real run.

## Current state

Hardened and green through review round three. Not yet submitted to the
shuttle, submission is a separate decision.

The seal boundary in one sentence. Everything in the table below cites
one netlist, the final hardened run and its sha256, while the waiver, the
datasheet, and this README describe that sealed package from outside it,
they are documentation, not new state.

| Number | Value |
|---|---|
| Final hardened run | CI 29401092054, commit 49f5f29 |
| Netlist sha256, the one hash | 5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0 |
| Standard cells | 1188, one tile, 64 percent utilization |
| Setup, worst corner max_ss_100C_1v60 | plus 1.556 ns at 50 MHz, TNS 0 |
| Hold, worst corner min_ff_n40C_1v95 | plus 0.111 ns, TNS 0, all nine corners met |
| DRC, LVS, antenna | 0, 0, 0 |
| Tests | 9 datapath plus 14 protocol white box RTL, 9 pin only gate level, all green |
| Formal | the async latency dimension proven unboundedly, yosys smtbmc with z3, induction closed, formal/README.md |
| Metastability MTBF bound | any tau below 351 ps outlives the universe age, extracted ss tau 134 ps, margin 2.6x, docs/CDC_MTBF.md |
| Known wart | max slew overage at the three ss corners and max tt, one waiver with two classes, characterized and waived with 1.56 ns of downstream slack, docs/WAIVERS.md |

## Pin map

Interface spec, docs/SPEC.md, frozen, the version lives inside the file.
Clock 50 MHz nominal.

| Pin | Dir | Role |
|---|---|---|
| ui_in[7:0] | in | Operand bus |
| uio[2:0] | in | Command |
| uio[3] | in | Strobe, async, synchronized inside |
| uio[4] | out | Busy |
| uio[5] | out | Overflow flag, sticky |
| uio[7:6] | out | Reserved, driven 0 |
| uo_out[7:0] | out | Selected accumulator byte, registered |

Commands, 000 NOP, 001 CLR, 010 LDA, 011 LDB, 100 MAC, 101 SEL_LO,
110 SEL_MID, 111 SEL_HI. One command per strobe rise. Driver rules and
timing requirements are in the spec, each interface requirement has a
pinning test that runs on the hardened netlist.

## Layout

```
src/    four design modules plus the Tiny Tapeout top and hardening config
tb/     white box RTL suites, golden model, local only
test/   pin only suite, runs at RTL and on the hardened netlist in CI
docs/   SPEC.md the frozen contract, CDC_MTBF.md the metastability bound,
        HOLD_REPORT.md, FANOUT_FF1.md, info.md the shuttle datasheet,
        cdc/ the extraction bench, sweeps, and replication gate
```

## How to test

```
# venv with cocotb 2.0.1 on Python 3.12, outside the repo
source ~/.venvs/mac8/bin/activate

# white box RTL suites
cd tb && make TB=datapath && make TB=top

# pin only suite at RTL, the same suite CI runs on the netlist
cd test && make

# lint
verilator --lint-only -Wall --top-module tt_um_arnav_mac8 \
  src/mac8_*.sv src/tt_um_arnav_mac8.sv
```

CI runs the Tiny Tapeout GDS action, the shuttle precheck, and the gate
level suite on every push.

## The story

The build log is TASK_LOG.md, findings first, dead ends kept. The short
version. Adversarial review with mutation testing is the primary gate, and
it caught what the green suites could not, an exact rail saturation gap, a
reset phantom command, an arm bit reading the metastable flop, a lockout
width that ate a legal command at an alignment no deterministic simulation
can produce, and a reset pin the harness never promised to synchronize.
Each fix is pinned by a test where a test can see it, and by a written
proof where one cannot.
