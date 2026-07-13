# mac8

Int8 serial multiply accumulate block for Tiny Tapeout. docs/SPEC.md is the frozen contract and it is law. On any ambiguity, stop and ask, do not decide.

## Layout

- src/mac8_datapath.sv, all data state, MAC math, saturation, sim only pulse guard
- src/mac8_sync.sv, strobe synchronizer, accept fires commands 2 to 3 clocks after the edge
- src/mac8_ctrl.sv, command decode, one pulse per accept, busy register
- src/mac8_top.sv, spec pin map, wiring only
- tb/golden.py, shared golden model, exact sat24
- tb/test_datapath.py, 9 unit tests. tb/test_top.py, 12 protocol tests
- docs/SPEC.md frozen v0.1. docs/SPEC_NOTES.md, the v0.2 change queue, not in force

## Commands

```
source ~/.venvs/mac8/bin/activate
cd tb && make                 # both suites
verilator --lint-only -Wall --top-module mac8_top src/*.sv
```

The venv lives outside the repo because the repo path contains spaces and make cannot handle them in include paths. Keep tb/Makefile source paths relative for the same reason.

## Rules

- always_ff and always_comb only. Nonblocking in sequential blocks. No latches. Lint must stay -Wall clean.
- Tests compare against tb/golden.py, never against the RTL's own math.
- Style for comments and docs. Short sentences. Periods and commas only. No em dashes. No semicolons.
- Commit in logical units, push each batch.

## Known toolchain traps

- cocotb 2.0.1 needs Python 3.13 or lower.
- Icarus $countones is broken, use explicit sums.
- $error only prints under cocotb. $fatal aborts the sim. The datapath guard uses $fatal.
- Delete sim_build_* before mutation runs, stale sims pass silently.

## Operating discipline

Adopted from OPERATING_MANUAL.md at the vault root. Evaluated 2026-07-13, not taken on faith.

- Keep TASK_LOG.md in this repo for in progress work. A Now field, plan units with exit checks, verified facts with how each was checked, dead ends.
- Write pass or fail acceptance criteria at task start. Re read the prompt clause by clause at the end against them.
- Before a multi file change, record the baseline test result, freeze the contract, cut units each with a named exit check, checkpoint after each.
- Walk the 10 item risk map to seed the review, record a check or not applicable for each. Boundaries, error paths, state transitions, concurrency, invariants, scale extremes, time, caching, resource lifecycles, unchanged callers.
- Label load bearing claims by evidence level. Never report reasoning as observation. Verify a file, signal, or API exists this session before citing it.
- Loop breaker. After the same command fails twice the same way, change approach or ask. No third identical retry.

Kept stronger than the manual, not replaced.

- Adversarial review with independent agents and mutation testing stays the primary bug gate, above a solo checklist. It caught the saturation flag gap on day 1 and the reset phantom on day 2.
- Always stop on SPEC.md ambiguity, stricter than the manual proceed default, because silicon bugs cannot be patched.
