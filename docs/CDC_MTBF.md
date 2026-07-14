---
tags: [chip-track, cdc]
project: P1
status: draft, constants extracted, MTBF argument pending Nav
---

# CDC MTBF

Constants extracted from the bench, threshold derived, values below. The
spoken MTBF argument is Nav's to write, placeholder heading at the bottom.

## Deliverables

| Item | Value |
|---|---|
| Cell characterized | sky130_fd_sc_hd__dfxtp_2, the netlist ff1, instance _1614_ |
| Probe node | xdut.a_466_413#, master latch storage node |
| Sweep data | docs/cdc/sweep_tt_94ab4266.csv, docs/cdc/sweep_ss_2160e2ac.csv |
| Deck hashes | 94ab4266 at tt, 2160e2ac at ss, sha256 of the session deck, first 8 hex |
| Fit script | scripts/fit_tau.py |
| Fit plots | docs/cdc/fit_tt.png, docs/cdc/fit_ss.png |
| tau at tt 025C 1v80 | 42.80 ps, R squared 0.8792 combined, 0.9986 and 0.9993 per side |
| T0 at tt 025C 1v80 | 20.17 ps |
| tau at ss 100C 1v60 | 131.49 ps, R squared 0.8914 combined, 0.9978 and 0.9991 per side |
| T0 at ss 100C 1v60 | 12.42 ps |
| Signoff corner | ss 100C 1v60, all bound numbers below use it |

## STA traceable inputs

The ff1 to ff2 synchronizer path, from the hardened netlist STA of CI run
29352875225, commit e82437b, the keep attribute run. Sources, the per corner
stapostpnr reports. Arrival and hold slack from the min.rpt path launched at
_1614_ ending at _1615_. Required time and capture clock from the max.rpt
endpoint block at _1615_. Setup slack is required minus arrival, same corner
directory, one liberty per corner. All values in ns.

| Value | nom_tt_025C_1v80 | max_ss_100C_1v60 |
|---|---|---|
| Launch clock arrival at ff1 CLK | 0.442575 | 0.774971 |
| Data path delay, ff1 CLK to ff2 D | 1.007156 | 2.014390 |
| Data arrival at ff2 D | 1.449731 | 2.789361 |
| Capture clock arrival at ff2 CLK | 20.439569 | 20.769043 |
| Clock uncertainty | 0.250000 | 0.250000 |
| Library setup time, dfxtp_2 | 0.107851 | 0.271807 |
| Setup required time | 20.081718 | 20.247238 |
| Setup slack, ff1 to ff2 | 18.631987 | 17.457877 |
| Hold slack, ff1 to ff2 | 0.788806 | 1.839709 |

Path cells in order, _1614_ dfxtp_2 Q, hold90 dlygate4sd3_1, _1553_ and2_2,
_1615_ dfxtp_2 D. The delay buffer and the reset AND are inside the data path
delay row.

## Extraction and bound

### Fit results

Model, resolution_time equals tau times ln(1 over offset) plus b. Fit,
numpy polyfit degree 1 on x equals ln(1 over absolute offset). T0 equals
exp(b over tau), from resolution_time equals tau times ln(T0 over offset).

| Corner | tau ps | T0 ps | intercept ns | R squared | points |
|---|---|---|---|---|---|
| tt 025C 1v80 | 42.80 | 20.17 | minus 1.0539 | 0.8792 | 20 |
| ss 100C 1v60 | 131.49 | 12.42 | minus 3.3021 | 0.8914 | 20 |

Per side robustness. The combined R squared reflects the two balance branches
carrying different intercepts, not nonlinearity.

| Corner, side | tau ps | T0 ps | R squared |
|---|---|---|---|
| tt, resolves to 1 | 41.64 | 10.44 | 0.99855 |
| tt, resolves to 0 | 43.95 | 37.62 | 0.99926 |
| ss, resolves to 1 | 128.80 | 6.44 | 0.99775 |
| ss, resolves to 0 | 134.19 | 23.34 | 0.99913 |

### Threshold derivation, worked

MTBF equals e to the (t over tau), over D, with D equals T0 times f_clk times
f_data.

Inputs, signoff corner ss 100C 1v60.

| Input | Value | Source |
|---|---|---|
| t | 17.457877 ns | ff1 to ff2 setup slack, STA table above |
| f_clk | 50 MHz | spec v0.3 nominal clock |
| f_data | 10 MHz | worst legal command rate, 5 clock rise to rise minimum |
| T0 | 12.42 ps | extracted, ss combined fit |
| MTBF floor A | 4.35e17 s | age of the universe |

Steps.

1. D equals 12.42e-12 times 50e6 times 10e6 equals 6210 per second.
2. Require e to the (t over tau) over D greater than A.
3. Multiply both sides by D. e to the (t over tau) greater than A times D.
4. A times D equals 4.35e17 times 6210 equals 2.701e21.
5. Take ln of both sides. t over tau greater than ln(2.701e21) equals 49.348.
6. Solve for tau. tau less than t over 49.348.
7. tau threshold equals 17.457877 ns over 49.348 equals 353.77 ps.

| Result | Value |
|---|---|
| Threshold tau, MTBF above the universe age | 353.77 ps |
| Extracted tau at ss | 131.49 ps |
| Margin, threshold over extracted | 2.69x |
| Margin against the worst per side ss tau, 134.19 ps | 2.64x |
| Threshold if T0 doubles to 23.34 ps | 349.30 ps, the exponent dominates |

## MTBF argument, to be written by Nav
