<!---
This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

MAC8 is a serial signed multiply accumulate unit, one step of a dot product per command. It multiplies two 8 bit signed operands into a 16 bit product and accumulates into a 24 bit signed accumulator, saturating at 8388607 and minus 8388608. Saturation sets a sticky overflow flag that only CLR clears. The accumulator reads out one byte at a time through a select register.

Inside there are three blocks. A synchronizer takes the asynchronous strobe through two flops, detects the rising edge, and fires one accept pulse per external edge, 2 to 3 core clocks after it. An arm bit blocks any accept until the strobe has been observed low after reset, and a lockout ignores further accepts for 4 clocks after any accept, so a slow or ringing strobe edge cannot fire twice. A decoder turns the accepted command code into exactly one control pulse. The datapath holds all data state and does the arithmetic.

Commands on uio[2:0], executed on strobe rise. 000 NOP. 001 CLR, accumulator and overflow flag to 0. 010 LDA and 011 LDB latch ui_in as signed operands. 100 MAC computes acc plus A times B with saturation. 101, 110, 111 select the low, middle, or high accumulator byte on uo_out.

The design is frozen against its interface spec, v0.2, kept in the project repository at docs/SPEC.md. The clock is 50 MHz nominal.

## How to test

Reset first. Hold the strobe low across reset release and for at least 3 clocks after it, the first command after reset needs the strobe observed low, then a fresh rise.

Drive one command per strobe rise. Set uio[2:0] and ui_in first, then raise the strobe. Hold it high at least 3 clocks and low at least 2 before the next rise. Hold the command and data stable the whole time the strobe is high and for 2 clocks after it falls.

Dot product of length N. CLR once. Per element, LDA x_i, then LDB w_i, then MAC. After the last element, SEL_LO, SEL_MID, SEL_HI, reading uo_out after each. Sample uo_out no earlier than 4 clocks after the SEL strobe rise. Reconstruct the 24 bit result from the three bytes and check the overflow flag on uio[5].

A quick smoke test. CLR, LDA 6, LDB 7, MAC, SEL_LO. uo_out reads 42.

## External hardware

None required. Any microcontroller with 12 free GPIO pins can drive it, 8 outputs to ui_in, 4 to uio[3:0], and 2 inputs from uio[5:4] plus 8 from uo_out. At GPIO toggle speeds the strobe timing rules are met with huge margin.

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
