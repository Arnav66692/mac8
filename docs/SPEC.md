---
tags: [chip-track, spec]
project: P1
version: "0.1"
status: frozen
---

# MAC8 Interface Spec v0.1

One page. This is the contract the RTL, the testbench, and the Tiny Tapeout integration all build against. Approving it freezes the interface. Changing it later costs a rebuild of all three.

## What the chip is

A serial signed multiply accumulate unit. 8 bit signed times 8 bit signed, accumulated into 24 bit signed with saturation. One multiplier, one accumulator, one command FSM. The atom of AI math, small enough to tape out, deep enough to interview on.

## Signals from the Tiny Tapeout harness

clk, the core clock. rst_n, active low reset, deassert treated as synchronous. ena, high when this design is selected, ignored internally in v0.1. ui_in[7:0], dedicated inputs. uo_out[7:0], dedicated outputs. uio[7:0], bidirectional with direction set statically by the design.

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

Commands arriving while busy is high are ignored. At demo board speeds, an MCU toggling GPIO, these numbers are trivially met.

## Reset state

acc 0. Overflow flag 0. Busy 0. Output select LO. uo_out 0.

## Timing

MAC completes 1 cycle after command accept in v0.1. Pipelining is a P3 topic. uo_out is registered, so it reflects any change one clock after the cause.

## Usage, dot product of length N

CLR once. Per element, LDA x_i, then LDB w_i, then MAC. After the last element, SEL_LO, SEL_MID, SEL_HI, reading uo_out after each. Check the overflow flag.

## Decisions baked in, challenge now or accept

1. Saturation, not wrapping.
2. Sticky overflow flag, cleared only by CLR.
3. One serial multiplier, no parallelism.
4. LDB and MAC stay separate commands. A fused LDB_MAC saves one cycle per element and can be v0.2 if tile area allows.

## Approval

Approved and frozen 2026-07-13. Changes from here are a version bump.

Links. [[P1 MAC RTL Block]], [[00 Chip Track Home]]
