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

## Evidence and remaining measurements

The original build's raw metrics, all nine post-route corner reports,
SDC and 15 passing prechecks are archived at reports/sealed/29401092054.
Their manifest verifies the downloaded raw netlist against the recorded
seal and records every archived file hash. This verifies an implementation
build, not payment or allocation in the submission portal.

Before adopting the fused candidate, inspect its separate hardened run,
precheck, gate-level application regression and routed corner results.
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
> operand-load/MAC protocol, with 1.28 percent higher mapped cell area under
> identical SKY130 synthesis conditions. Proved scheduling invariants and
> mutation-tested stale operands, missing execution and busy signaling.

For silicon, replace simulated cycles with measured system throughput
only after archiving the board run. Do not claim a completely formally
verified chip, measured energy savings or silicon speedup from this record.
