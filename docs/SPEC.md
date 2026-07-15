---
tags: [chip-track, spec]
project: P1
version: "0.4"
status: frozen
---

# MAC8 Interface Spec v0.4

Changelog. 2026-07-15, v0.4 frozen, no feature changes, two round two corrections. First, the lockout width corrected from 4 clocks to 3, a 4 clock window ate a legal command at worst async alignment. One added sentence, spacing is measured in core clocks and an asynchronous driver owns its own frequency error against those clocks. Second, rst_n is now synchronized inside the design. The Tiny Tapeout harness handles clk and rst_n like any other input pins, its clock spec says so, so rst_n at the pad is asynchronous. A two flop synchronizer was added, and the reset rule clock counts moved by the 2 clock crossing. After the round three proof the lockout violation row is stated as best effort, resolution dependent below the legal spacing, wording only.

Changelog. 2026-07-14, v0.3 frozen, interface requirements formalized, no feature changes. Two prior driver rules became stated requirements with defined violation behavior and a named pinning test each, see Interface requirements below.

Changelog. 2026-07-13, v0.2 frozen, clarifications only, no feature changes. Three additions. A SEL read rule. A reset strobe low rule with the measured arm time. The nominal clock.

One page. This is the contract the RTL, the testbench, and the Tiny Tapeout integration all build against. Approving it freezes the interface. Changing it later costs a rebuild of all three.

## What the chip is

A serial signed multiply accumulate unit. 8 bit signed times 8 bit signed, accumulated into 24 bit signed with saturation. One multiplier, one accumulator, one command FSM. The atom of AI math, small enough to tape out, deep enough to interview on.

## Signals from the Tiny Tapeout harness

clk, the core clock, 50 MHz nominal on the Tiny Tapeout harness. rst_n, active low reset, asynchronous at the pad. The Tiny Tapeout clock spec states that both the clk and rst_n pins are handled like any other input pins, no harness synchronization, tinytapeout.com/specs/clock. The design synchronizes rst_n through two flops, assertion and release reach the core 2 clocks after the pad. ena, high when this design is selected, ignored internally in v0.1. ui_in[7:0], dedicated inputs. uo_out[7:0], dedicated outputs. uio[7:0], bidirectional with direction set statically by the design.

## Pin map

| Pin | Dir | Role |
|---|---|---|
| ui_in[7:0] | in | Operand bus |
| uio[2:0] | in | Command |
| uio[3] | in | Strobe, async, synchronized inside |
| uio[4] | out | Busy |
| uio[5] | out | Overflow flag, sticky |
| uio[7:6] | out | Reserved, driven 0 |
| uo_out[7:0] | out | Selected accumulator byte, registered |

uio_oe is static. Bits 3 to 0 are inputs. Bits 7 to 4 are outputs.

## Commands on uio[2:0], executed on strobe rise

| Code | Name | Effect |
|---|---|---|
| 000 | NOP | Nothing |
| 001 | CLR | Accumulator to 0, overflow flag to 0 |
| 010 | LDA | Latch ui_in as operand A, signed |
| 011 | LDB | Latch ui_in as operand B, signed |
| 100 | MAC | acc = sat24 of acc plus A times B |
| 101 | SEL_LO | uo_out shows acc[7:0] |
| 110 | SEL_MID | uo_out shows acc[15:8] |
| 111 | SEL_HI | uo_out shows acc[23:16] |

## Arithmetic

Operands are two's complement int8. The product is int16. Accumulation is int24, saturating at 8388607 and minus 8388608. Saturation sets the sticky overflow flag. Only CLR clears it.

## Strobe and data contract

The strobe is asynchronous and crosses into the core clock domain through a 2 flop synchronizer with edge detect. A command fires once per rising edge, 2 to 3 core clocks after the external edge.

Driver rules:
1. Set uio[2:0] and ui_in first. Then raise strobe.
2. Hold strobe high at least 3 core clocks. Hold it low at least 2 before the next rise.
3. Hold ui_in and uio[2:0] stable the whole time strobe is high and for 2 clocks after it falls.

Commands arriving while busy is high are ignored. A ringing or slow strobe edge that crosses the threshold twice fires only once. The design ignores further accepts for 3 clocks after any accept, and the minimum legal rise to rise spacing is 5 clocks, so a compliant driver never loses a command, including at the worst async alignment where accepts from two legal rises land 4 clocks apart. Below the legal spacing the lockout is best effort, whether a sub contract rise passes or blocks depends on which edge resolves slow, the requirements table states it. At demo board speeds, an MCU toggling GPIO, these numbers are trivially met.

## Interface requirements

These were driver guidance in v0.2. In v0.3 they are stated requirements with defined violation behavior and a pinning test each. Clocks are core clocks at 50 MHz, 20 ns each. Spacing is measured in core clocks, and an asynchronous driver owns its own frequency error against those clocks.

| Requirement | Value | Violation behavior | Pinning test |
|---|---|---|---|
| Rise to rise spacing | at least 5 clocks between strobe rises | Best effort below the legal spacing, resolution dependent. A rise whose accept lands inside the 3 clock lockout after a prior accept is ignored. At spacing 4 a slow then fast resolution blocks the second rise and the other combinations pass it. At or above 5 clocks no command is ever lost at any resolution, proven in formal/f_handshake.sv and enumerated by test_latency_grid | test_lockout_boundary_gl, test_latency_grid |
| Data setup and hold | ui_in and uio[2:0] stable from before the strobe rise, through the whole high time, and for 2 clocks after the fall | Data changed inside that window can be captured or missed, the command latches an undefined value, outside the window it has no effect | test_data_hold_window |

Both pinning tests are pin only and run on the hardened gate level netlist, not just RTL.

## Read rule

After a SEL command, sample uo_out no earlier than 4 clocks after the strobe rise. That is 3 clocks for the sync path plus 1 for the registered output.

## Reset state

acc 0. Overflow flag 0. Busy 0. Output select LO. uo_out 0.

## Reset rule

Hold rst_n low at least 3 clocks for the reset to take effect, 2 to cross the internal synchronizer and 1 to act. Hold strobe low across reset release. The first command after reset requires strobe observed low, then a fresh rise. Hold strobe low at least 5 clocks after release before that first rise. The release crosses the 2 clock synchronizer, then the arm settles 3 internal clocks later, the fifth clock after the pad release. The derived hard floor is 3 clocks, and a rise at release itself is read as strobe high across reset and dropped. Counts before v0.4 were 3 and 1, measured without the reset synchronizer.

## Timing

MAC completes 1 cycle after command accept in v0.1. Pipelining is a P3 topic. uo_out is registered, so it reflects any change one clock after the cause.

## Usage, dot product of length N

CLR once. Per element, LDA x_i, then LDB w_i, then MAC. After the last element, SEL_LO, SEL_MID, SEL_HI, reading uo_out after each. Check the overflow flag.

## Decisions baked in, challenge now or accept

1. Saturation, not wrapping.
2. Sticky overflow flag, cleared only by CLR.
3. One serial multiplier, no parallelism.
4. LDB and MAC stay separate commands. A fused LDB_MAC saves one cycle per element and is queued in SPEC_NOTES.md for a future feature version, not v0.2.

## Approval

Approved and frozen at v0.1 on 2026-07-13. v0.2 clarifications frozen 2026-07-13, no feature changes, wording only. v0.4 corrections frozen 2026-07-15 on the round two ruling. Changes from here are a version bump.

Links. [[P1 MAC RTL Block]], [[00 Chip Track Home]]
