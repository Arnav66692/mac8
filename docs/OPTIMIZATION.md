# MAC8 DSP application and fused-load experiment

## Problem and result

Every fresh pair needs LDA, LDB and MAC in the baseline. The multiplier is
already available between most host commands. Combining B load with a
scheduled MAC removes one transaction per term without another multiplier.

The executable driver uses seven clocks per command, including setup and
hold margin. For a 16-term output and three-byte result read, the baseline
uses 52 commands, or 364 simulated cycles. The fused candidate uses 36
commands, or 252 cycles. This is 30.77 percent fewer cycles and 1.444 times
equivalent target-clock throughput. At an assumed 50 MHz the times are
7.28 and 5.04 microseconds. These are simulation cycle measurements.
Physical host overhead is excluded.

The original minimum-spacing protocol limits were 260 and 180 clocks.
The working driver intentionally includes setup and hold margin, so those
ideal limits are not the numbers used by the application report.

## Implementation

The candidate gives opcode 000 the versioned LDB_MAC meaning. It latches B
on acceptance and performs MAC on the following clock. A pending bit
prevents accepting another command during scheduling, and a following busy
bit retains the completion window. Legal command spacing is longer than
both windows. Reset cancels pending work once synchronized reset acts.

The baseline RTL and Tiny Tapeout source list retain their existing
interface. The candidate is under experiments/fused and has a separate
module name and specification. The fused workflow stages its metadata
inside that job only, builds it with the same SKY130 flow, and runs the
application on that run's powered netlist. This is an experiment, not a
portal submission.

## Local synthesis comparison

| Metric | Baseline | Fused |
|---|---:|---:|
| Mapped cells | 805 | 811 |
| Mapped cell area, square micrometers | 6152.1504 | 6230.9760 |
| Area change | Reference | Plus 1.28 percent |

Both use Yosys 0.67+post, the same SKY130 HD typical-corner Liberty and a
20000 ps ABC mapping target. This is a local mapping comparison. It is
different from the historical 1188-cell post-route baseline, where clock,
hold and physical repair cells also exist. It does not establish candidate
Fmax, power, fit or post-route area.

```sh
python scripts/compare_synthesis.py --liberty "$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
python scripts/render_dsp_report.py
```

Report rendering additionally needs numpy and matplotlib. Raw results,
source hashes, logs, plot and input/output CSV live in reports/dsp-demo.
The renderer refuses stale source hashes, incomplete regressions,
unfinished proof/mutation runs or altered historical reports.

## Routed comparison, completed 2026-10-04

The baseline and fused candidate were hardened at the same source commit,
9ac84c5. Post-route configuration differs only in DESIGN_NAME. Both use
LibreLane 3.0.5 and SKY130 PDK 8afc8346. Both runs and all downstream checks
pass. The baseline netlist is byte-identical to the historical seal.

| Routed result | Baseline | Fused |
|---|---:|---:|
| Standard cells | 1188 | 1203 |
| Standard-cell area, square micrometers | 10547.6 | 10704.0 |
| Utilization, percent | 63.95 | 64.90 |
| Worst setup slack, ns | +1.556 | +0.702 |
| Worst hold slack, ns | +0.111 | +0.114 |
| Worst-corner max-transition violations | 254 | 282 |
| DRC, LVS, antenna errors | 0, 0, 0 | 0, 0, 0 |
| Tiny Tapeout prechecks | 15 of 15 | 15 of 15 |

Routed standard-cell area increases **1.48 percent**. Setup and hold meet
across all nine corners. The candidate's powered netlist passes the nine
application tests, including the full 100000-operation soak and exact FIR
outputs. These are functional gate simulations. The existing baseline's
14-test SDF job also passes on its freshly generated netlist and SDF.

The transition violations remain, with a larger count on the candidate.
Its slow-corner maximum reported slew is 1.225 ns against the 0.750 ns
limit. Existing W1 acceptance does not approve the candidate. Keep the
fused design experimental until a separate transition and waiver review.
The reduced cycles do not justify claiming a higher clock rate or lower
energy use.

[Baseline build](https://github.com/Arnav66692/mac8/actions/runs/37242546187),
[fused build](https://github.com/Arnav66692/mac8/actions/runs/37242546160),
[comparison manifest](../reports/dsp-demo/routed-comparison.json) and
[source-matched DSP CI](https://github.com/Arnav66692/mac8/actions/runs/37242546203).
Raw metrics, per-corner checks, configuration, prechecks and the candidate
application captures are archived under reports/routed with file hashes.

## Evidence and remaining measurements

The original build's raw metrics, all nine post-route corner reports,
SDC and 15 passing prechecks are archived at reports/sealed/29401092054.
Their manifest verifies the downloaded raw netlist against the recorded
seal and records every archived file hash. This verifies an implementation
build, not payment or allocation in the submission portal.

Before adopting the fused candidate, review its transition exceptions and
confirm the intended portal revision. Its hardening, precheck, gate-level
application regression and routed corner results are now archived.
Keep W1 max-transition exceptions visible. Measure physical FIR throughput
and host-software runtime using app/board_demo.py when the actual design
is available on a board. Submission receipt, fabrication and silicon
validation remain separate milestones.

## Resume wording

Current application and optimization evidence supports these lines.

> Implemented a host-controlled 16-tap INT8 FIR application with bit-exact
> pin-level verification, exhaustive testing of 65536 signed operand pairs
> and 200000 scheduled operations across baseline and optimized RTL.

> Reduced FIR execution from 364 to 252 simulated cycles through a fused
> operand-load/MAC protocol, with 1.48 percent higher routed standard-cell area under
> identical SKY130 implementation conditions and nine-corner setup/hold met. Proved scheduling invariants and
> mutation-tested stale operands, missing execution and busy signaling.

For silicon, replace simulated cycles with measured system throughput
only after archiving the board run. Do not claim a completely formally
verified chip, measured energy savings or silicon speedup from this record.
