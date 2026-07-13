# mac8

Int8 serial multiply accumulate block for Tiny Tapeout. docs/SPEC.md is the frozen contract and it is law. On any ambiguity, stop and ask, do not decide.

## Layout

- src/mac8_datapath.sv, all data state, MAC math, saturation, sim only pulse guard
- src/mac8_sync.sv, strobe synchronizer, accept fires commands 2 to 3 clocks after the edge
- src/mac8_ctrl.sv, command decode, one pulse per accept, busy register
- src/mac8_top.sv, spec pin map, wiring only
- tb/golden.py, shared golden model, exact sat24
- tb/test_datapath.py, 9 unit tests. tb/test_top.py, 9 protocol tests

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
- $error cannot fail a cocotb test, grep logs for guard messages.
- Delete sim_build_* before mutation runs, stale sims pass silently.
