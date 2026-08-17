---
tags: [chip-track, signoff]
project: P1
status: timing annotated gate level pass, 14 tests at the revision run corner
---

# Timing annotated gate level result

Finding first, kept for the record. The round three version of this
result was false. The annotation hook was compiled but never elaborated,
cocotb names only tb as an iverilog root, so $sdf_annotate never ran and
every specify path sat at zero delay. The missing file probe that claimed
to confirm annotation could not have failed, Icarus 13 is silent on a
missing SDF file even when the call runs. That is incident 10 in the
project log. Everything below is from the rebuilt flow, which proves
annotation liveness on every run.

## What ran

The full 14 test pin only suite, test/test.py, including
test_sel_read_floor, on the powered gate level netlist with the corner
SDF back annotated. Icarus 13 with gspecify and ginterconnect, the
sky130 timing models, the 20 ns project clock. Entry point
scripts/run_gl_sdf.sh, which owns the pass or fail decision. The hook is
an explicit elaboration root and its banners, the annotate call in the
compiled binary, the blessed structural identity of the SDF, and a full
message census against the SDF file are all required before a result
counts.

## Corner and provenance

max_ss_100C_1v60, the slow signoff corner. The SDF is
tt_um_arnav_mac8__max_ss_100C_1v60.sdf from the revision run
31284819649, commit 715897d, sha256
062ff035000a22c91b58233ae55e18a5e49272825ec051e321b6c6b5c74de5d8,
kept locally as test/sdf_max_ss.sdf. The raw netlist of that run is byte
identical to the sealed run's, sha256 5d414931, and the powered netlist
the sim runs is byte identical too, sha256 5c51d76c.

The delta against the sealed run's SDF, ccb9d44e from run 29401092054,
is characterized, not assumed. With the DATE, PROGRAM, and VERSION
header lines stripped, both files reduce to the same structural sha256,
b637fd18, zero differing lines. Every IOPATH, INTERCONNECT, and
TIMINGCHECK value is byte identical, OpenSTA 2.7.0 wrote both. The
LibreLane 3.0.3 to 3.0.5 bump moved no delay. Header only, closed.
OpenSTA at the submitted run stays the setup and hold authority either
way, this sim proves function under those delays, not the windows.

## Result

Pass. All 14 pin tests pass with live annotation at the 20 ns project
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
test/measure_delay.py on this run's SDF. The annotated number is the
extracted corner delay, the functional number is the fixed one unit
delay.

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

## The gate and its controls

The runner classifies every SDF runtime message by its stable message
body, the third audit closed a false fail where cocotb output interleaved
into the file and line prefix the old census parsed. Class counts must
equal counts recomputed from the SDF file, any unclassified message
fails, any unmatched instance fails, and the SDF must match a blessed
structural hash, so a tampered or truncated file is rejected before the
sim runs. Controls, each watched failing. A missing file fails. A
deliberately mismatched SDF fails with unmatched instance errors. A
deliberately deleted TIMINGCHECK section fails the structural identity.
Reproduce with scripts/run_gl_sdf.sh --missing, --mismatch, and
--deleted-section.
