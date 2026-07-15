---
tags: [chip-track, cdc]
project: P1
status: complete, round two hardened, conservative headline
---

# CDC MTBF

Constants extracted from the bench, threshold derived, values below. The
spoken MTBF argument is written in the section at the bottom. Round two
promoted the worst per side pair as the headline, the combined fit is a
two line model violation by our own R squared diagnosis. Every table here
cites the final hardened run, one netlist hash for the whole package.

## Deliverables

| Item | Value |
|---|---|
| Final hardened run | CI run 29401092054, commit 49f5f29, netlist sha256 5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0 |
| Cell characterized | sky130_fd_sc_hd__dfxtp_2, the netlist ff1, instance _1624_ in the final run |
| Cell netlist | docs/cdc/dfxtp_2.spice, the PDK extracted cell netlist, 28 lines, sha256 26e32b3c4f62819c2253c4ebded610e5a6a9faca3c68875c5820c364c1551632 |
| Cell netlist source | sky130_fd_sc_hd.spice in the volare sky130A PDK, open_pdks c6d73a35, sha256 6dec6626decd1ee15afacafab9925b1a336ab344b7b5e1bec9d7483f2a6badc3 |
| Probe node | xdut.a_466_413#, master latch storage node |
| Sweep data | docs/cdc/sweep_tt_94ab4266.csv, sweep_ss_2160e2ac.csv, plus round two reruns sweep_ss_0fcc822d.csv real slews and sweep_ss_f6bb1d1f.csv solver check |
| Deck hashes | 94ab4266 tt, 2160e2ac ss, 0fcc822d ss real slews, f6bb1d1f ss solver check, sha256 of the session deck, first 8 hex, the deck text carries every stimulus and solver value |
| Fit script | scripts/fit_tau.py |
| Fit plots | docs/cdc/fit_tt.png, docs/cdc/fit_ss.png |
| Headline tau at ss 100C 1v60 | 134.19 ps, the worst per side fit, R squared 0.9991 |
| Headline T0 at ss 100C 1v60 | 23.34 ps, same per side fit |
| Combined tau at ss 100C 1v60 | 131.49 ps, R squared 0.8914 combined, 0.9978 and 0.9991 per side, reference only, the combined fit is a two line model violation |
| Combined T0 at ss 100C 1v60 | 12.42 ps, reference only |
| tau at tt 025C 1v80 | 42.80 ps, R squared 0.8792 combined, 0.9986 and 0.9993 per side |
| T0 at tt 025C 1v80 | 20.17 ps |
| Signoff corner | ss 100C 1v60, all bound numbers below use it |
| MTBF argument | written, section MTBF for the strobe synchronizer below |
| Fanout evidence | docs/FANOUT_FF1.md, ff1 Q drives the hold buffer and nothing else |

## STA traceable inputs

The ff1 to ff2 synchronizer path, from the final hardened netlist STA of CI
run 29401092054, commit 49f5f29, the round two run with the lockout width
fix and the rst_n synchronizer in. Sources, the per corner stapostpnr
reports. Arrival and hold slack from the min.rpt path launched at _1624_
ending at _1625_. Required time and capture clock from the max.rpt endpoint
block at _1625_. Setup slack is required minus arrival, same corner
directory, one liberty per corner. All values in ns.

| Value | nom_tt_025C_1v80 | max_ss_100C_1v60 |
|---|---|---|
| Launch clock arrival at ff1 CLK | 0.417493 | 0.735318 |
| Data path delay, ff1 CLK to ff2 D | 0.962098 | 1.933987 |
| Data arrival at ff2 D | 1.379591 | 2.669305 |
| Capture clock arrival at ff2 CLK | 20.417534 | 20.735399 |
| Clock uncertainty | 0.250000 | 0.250000 |
| Library setup time, dfxtp_2 | 0.108732 | 0.271606 |
| Setup required time | 20.058802 | 20.213793 |
| Setup slack, ff1 to ff2 | 18.679211 | 17.544488 |
| Hold slack, ff1 to ff2 | 0.740827 | 1.753611 |

Path cells in order, _1624_ dfxtp_2 Q, hold84 dlygate4sd3_1, _1563_ and2_2,
_1625_ dfxtp_2 D. The delay buffer and the reset AND are inside the data
path delay row. Complete fanout evidence in docs/FANOUT_FF1.md.

Why ss 100C 1v60 bounds tau. tau grows with lower voltage and higher
temperature, and the extraction confirms the direction, 42.80 ps at tt
1.80 V 25 C against 131.49 ps at ss 1.60 V 100 C, so the slowest corner in
the signoff set is the tau maximum and the bound below prices it. The ss
extraction supply is 1.60 V, the low supply corner, 11 percent below the
1.80 V nominal, so board droop is already priced, no additional low
voltage point is needed.

The slack feeding the exponent carries clock uncertainty. t is required
minus arrival, and required already subtracts the 0.25 ns uncertainty and
the library setup time, so t is net of both, conservative direction.
f_data is an input assumption, not a derived value, 10 MHz worst legal,
one strobe rise per 5 clocks at 50 MHz. The denominator is linear in it,
halving the rate doubles the MTBF, it must be stated, never reverse
engineered from the answer.

Scope of this bound. It covers the strobe crossing, ff1 to ff2 in
mac8_sync. The reset synchronizer, rst_ff1 and rst_ff2 in mac8_rst_sync,
instances _1636_ and _1635_ in the final netlist, is the same
sky130_fd_sc_hd__dfxtp_2 cell, so tau and T0 carry over. It is outside
the f_data rate model above, its event rate is one transition per reset,
not 10 MHz, so its MTBF sits about seven orders of magnitude beyond the
strobe bound at the same slack scale. Stated for scope, the headline
number is the strobe path.

### Threshold delta trace, round two to the final run

Last round the headline read threshold 353.77 ps and margin 2.69x. The
final package reads 351.04 ps and 2.62x. The 2.73 ps delta decomposes into
two moves, both traceable.

| Move | Threshold | Traces to |
|---|---|---|
| Round two basis, t 17.457877 ns, combined T0 12.42 ps | 353.77 ps | run 29352875225, commit e82437b |
| Slack moved to 17.544488 ns, same T0 | 355.53 ps, plus 1.76 | run 29401092054, commit 49f5f29, the F3 width fix and the rst_n synchronizer re placed the netlist, launch 0.774971 to 0.735318, data path delay 2.014390 to 1.933987 |
| T0 promoted to the worst per side 23.34 ps | 351.04 ps, minus 4.49 | the round two conservative headline ruling, ln factor 49.348 to 49.979 |

The refit did not move tau. The sweep CSVs and the fit are unchanged from
round two, tau reads 131.49 combined and 134.19 worst per side in both.
The ratio moved 2.69 to 2.62 for the same two reasons plus the tau basis
promotion, 131.49 to 134.19, in the denominator of the margin.

Free margin, noted, not claimed. The bench measures band exit on the master
latch node, upstream of the Q pin that STA references. A real failure needs
the resolution to outlast the slack plus the clock to master capture time
plus the regeneration to Q, so setting t equal to the bare slack under
credits the margin. Conservative direction, the bound stands without it.

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
carrying different intercepts, not nonlinearity. That makes the combined fit
a two line model violation by our own diagnosis, so the worst per side pair
is the headline, tau 134.19 ps and T0 23.34 ps.

| Corner, side | tau ps | T0 ps | R squared |
|---|---|---|---|
| tt, resolves to 1 | 41.64 | 10.44 | 0.99855 |
| tt, resolves to 0 | 43.95 | 37.62 | 0.99926 |
| ss, resolves to 1 | 128.80 | 6.44 | 0.99775 |
| ss, resolves to 0, headline | 134.19 | 23.34 | 0.99913 |

Round two robustness reruns at ss, both committed with deck hashes.

| Run | tau ps combined | T0 ps combined | worst per side tau ps | Verdict |
|---|---|---|---|---|
| Baseline, 20 ps edges, gear, reltol 1e-6 | 131.49 | 12.42 | 134.19 | reference |
| Real STA slews, CLK 75.9 ps, D 69.3 ps | 131.02 | 16.25 | 131.83 | tau moved 0.4 percent, stimulus attack removed |
| Solver check, reltol 1e-7, max step halved, trap | 131.42 | 12.46 | 134.00 | tau moved under 0.1 percent, physics not integrator |

The worst per side tau across all three runs is the baseline 134.19 ps, so
the headline pair survives its own robustness checks. The real slew values
came from the prior run's STA, the final run reads ff1 CLK slew 82.3 ps,
the conclusion is unchanged, tau moved 0.4 percent across a 4x edge change.

### Threshold derivation, worked

MTBF equals e to the (t over tau), over D, with D equals T0 times f_clk times
f_data.

Inputs, signoff corner ss 100C 1v60, headline conservative pair.

| Input | Value | Source |
|---|---|---|
| t | 17.544488 ns | ff1 to ff2 setup slack, STA table above, final run |
| f_clk | 50 MHz | spec nominal clock |
| f_data | 10 MHz | worst legal command rate, 5 clock rise to rise minimum |
| T0 | 23.34 ps | extracted, ss worst per side fit, the headline |
| MTBF floor A | 4.35e17 s | age of the universe |

Steps.

1. D equals 23.34e-12 times 50e6 times 10e6 equals 11670 per second.
2. Require e to the (t over tau) over D greater than A.
3. Multiply both sides by D. e to the (t over tau) greater than A times D.
4. A times D equals 4.35e17 times 11670 equals 5.076e21.
5. Take ln of both sides. t over tau greater than ln(5.076e21) equals 49.979.
6. Solve for tau. tau less than t over 49.979.
7. tau threshold equals 17.544488 ns over 49.979 equals 351.04 ps.

| Result | Value |
|---|---|
| Threshold tau, MTBF above the universe age | 351.04 ps |
| Headline extracted tau at ss, worst per side | 134.19 ps |
| Margin, threshold over headline | 2.62x |
| Margin against the combined ss tau, 131.49 ps | 2.67x |
| Threshold on the combined pair, T0 12.42 ps | 355.53 ps, margin 2.70x, reference |
| Threshold if T0 doubles to 46.68 ps | 346.24 ps, the exponent dominates |
| Threshold at the real slew rerun T0, 32.66 ps | 348.71 ps, same story |

Sensitivity against an extraction miss, headline basis, D 11670 per second,
t 17.544488 ns. The Beer and Ginosar 65 nm test chip, The Devolution of
Synchronizers, IEEE ASYNC 2010, measured 3.3x over its own prediction, so
the table brackets a miss of that size.

| tau | MTBF | Read as |
|---|---|---|
| 134.19 ps, extracted | 5.2e52 s | 1.2e35 universe ages |
| 268.4 ps, 2x miss | 2.1e24 s | 6.7e16 years, 4.8 million universe ages |
| 442.8 ps, 3.3x miss, the Beer and Ginosar factor | 1.4e13 s | about 437 thousand years, silicon outlived |
| 536.8 ps, 4x miss | 1.3e10 s | about 426 years, still past any part lifetime |

The bound survives a 65 nm sized extraction miss. The measured 3.3x factor
from the Beer and Ginosar chip leaves six orders of magnitude past a
century. Only a miss beyond 4x brings the number into engineering range at
all, and it is still centuries.

## MTBF for the strobe synchronizer

This analysis proves the physical metastability margin of the strobe synchronizer. It does not prove the RTL protocol. RTL simulation resolves deterministically and cannot exhibit metastability, so the 23 white-box tests and 9 gate-level tests prove protocol behavior and this analysis proves the physics.

The standard estimate is:

MTBF = e^(t/tau) / (T0 · f_clk · f_data)

Here, t is the settling time the design grants ff1 before ff2 samples it. tau is the metastability resolution time constant of the flop. T0 is the effective metastability window of the flop. f_clk is the sampling clock frequency. f_data is the asynchronous input transition rate.

Use signoff numbers, not convenient numbers. The settling time t is the STA setup slack on the ff1 to ff2 path from the hardened netlist, 17.54 ns at the ss signoff corner. That slack already includes the inserted hold buffer and the reset AND gate, so those cells are priced into the margin. The clock is 50 MHz. The async transition rate is 10 MHz, one legal strobe rise every five clocks, the worst the spec permits. That is worst legal traffic, not typical demo-board traffic, so it makes the answer more pessimistic.

The flop parameters are extracted, not looked up, because no foundry ships them directly. The extracted values are tau 42.8 ps and T0 20.2 ps at nominal, and tau 134.2 ps and T0 23.3 ps at the ss corner, the worst per side pair. The combined ss fit reads tau 131.5 ps and T0 12.4 ps, but the combined fit is a two line model violation by our own R squared diagnosis, the two resolve directions carry different intercepts, so the worst per side pair is the honest number. The extraction method is SPICE on the exact dfxtp_2 cell from the netlist, probing the master latch node, with the deck hash recorded in the deliverable table.

Use this as a bound, not just a point estimate. The question is how bad tau could be before the MTBF drops below the age of the universe. Solve:

tau_threshold = t / ln(age_of_universe · T0 · f_clk · f_data)

Using the ss corner denominator from the report, T0 · f_clk · f_data = 11670 per second, and the age of the universe, 4.35e17 seconds, the threshold is:

tau_threshold = 17.54 ns / ln((4.35e17) · 11670) = 351.0 ps

The extracted ss value is tau 134.2 ps, so the real extracted value is 351.0 / 134.2 = 2.62 times inside the threshold. The bound reads in three tiers. The universe age line holds through any extraction miss up to 2.62x. The one measured precedent, the Beer and Ginosar 65 nm chip, missed its own prediction by 3.3x, which lands past that line at 1.4e13 seconds, about 437 thousand years, the table row. Even a 4x miss leaves about 426 years on a tile whose worst failure is a glitch on a demo board.

The result is also insensitive to T0. T0 sits inside a logarithm, so even a 2x error in it moves the threshold by about 1 percent. The bound does not rest on precise silicon numbers.

This is still an analysis, not measured silicon. SPICE is not silicon, and the real number would require measured foundry data or a metastability test structure, which this project did not build because there is one flagship. But the margin is large enough that the conclusion survives that gap.
