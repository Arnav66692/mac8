# MAC8 fused-load DSP candidate

## How it works

One signed 8-bit multiplier feeds a 24-bit saturating accumulator. A fused
operand-load command reduces a fresh pair from three transactions to two.
The host manages sample history and coefficients for a 16-tap FIR demo.

This is an experimental protocol. Opcode 000 means LDB_MAC, unlike baseline
NOP. LDA remains 010. The fused command loads B, then schedules its MAC on
the next clock. CLR, LDB, ordinary MAC and all three byte selections retain
their baseline opcode values. Inputs must remain stable through the strobe
high time and two clocks afterward. Result reads wait at least five clocks
after a SEL strobe rise. See experiments/fused/SPEC.md.

## How to test

Run make -C verification VARIANT=fused. The suite checks signed vectors,
new-B use, FIR responses, both saturation rails, sticky overflow, reset,
busy, byte read timing and a reproducible 100,000-operation command soak.
The same application runs on a functional hardened gate netlist using
VARIANT=fused-gate. The candidate scheduling proof and mutation checks
are separate scripts. Physical measurements require received hardware.

## External hardware

Use an externally clocked Tiny Tapeout board and a host driving ui_in and
uio bits 0 through 3, reading uo_out and uio bits 4 through 7. Start the clock
before reset. Hold pad reset low for six clocks and strobe low for eight
clocks after release in the supplied conservative driver.
