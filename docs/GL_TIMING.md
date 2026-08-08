---
tags: [chip-track, signoff]
project: P1
status: timing annotated gate level pass, rebuilt after incident 10
---

# Timing annotated gate level result

Finding first. The round three version of this result was false. The
annotation hook was compiled but never elaborated, cocotb names only tb
as an iverilog root, so $sdf_annotate never ran and every specify path
sat at zero delay. The missing file probe that claimed to confirm
annotation could not have failed, Icarus 13 is silent on a missing SDF
file even when the call runs. That is incident 10 in the project log. The
prior claim is retracted. Everything below is from the rebuilt flow,
which proves annotation liveness on every run.

## What ran

The nine test pin only suite, test/test.py, on the powered gate level
netlist of the final hardened run, with the corner SDF back annotated.
Icarus 13 with gspecify and ginterconnect, the sky130 timing models, the
20 ns project clock. Entry point scripts/run_gl_sdf.sh, which owns the
pass or fail decision. The hook is an explicit elaboration root and its
banners, the annotate call in the compiled binary, and a full message
census against the SDF file are all required before a result counts.

## Corner

max_ss_100C_1v60, the slow signoff corner. The SDF is
tt_um_arnav_mac8__max_ss_100C_1v60.sdf from CI run 29401092054, commit
49f5f29, raw netlist sha256
5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0.

## Result

Pass. All 9 pin tests pass with live annotation at the 20 ns project
clock. The run covers the power up X window, every gate level flop
starts X and the reset tests pass through that window with annotated
delays.

Annotation statistics, recounted from the file by the run script.

| Item | Count | Applied |
|---|---|---|
| Cells | 1900 | yes |
| IOPATH delays | 2503 | yes |
| INTERCONNECT delays | 2231 | 2217 applied, 14 zero delay tie cell entries into the static uio pins are reported unmatched, no timing content |
| TIMINGCHECK sections | 63 | no, see scope |
| Header corner form lines | 2 | metadata, no delay content |

Liveness evidence, beyond the census. The first uo_out transition after
its launching clock edge measures 1451 ps annotated against 1000 ps in
the functional unit delay sim, same netlist, same clock, measured by
test/measure_delay.py. The annotated number is the extracted corner
delay, the functional number is the fixed one unit delay.

## Scope, what this run does and does not prove

Icarus applies propagation delays but implements no timing checks. The
63 TIMINGCHECK sections in the SDF, the setup, hold, and width windows,
are not applied, and the compile discards the check constructs in the
cell models. So this sim cannot detect a setup or hold violation. Those
windows are signed by OpenSTA across the nine corners, docs/HOLD_REPORT.md
and the sealed run reports. What this run proves is functional behavior
under real corner propagation delays, the netlist reaches a clean reset
state through the X window and matches the golden model at the pins at
50 MHz.

## Negative controls

Both run on demand and both must fail for the positive result to mean
anything. A missing SDF file fails the gate, the file existence check
and the message census both catch it, silence is never success. A
deliberately mismatched SDF, every instance name perturbed, fails the
gate with unmatched instance errors and the suite itself breaks, 7 of 9
tests fail, because interconnect delays apply against zero cell delays.
Reproduce with scripts/run_gl_sdf.sh --missing and --mismatch.
