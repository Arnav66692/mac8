# mac8

Int8 serial MAC for Tiny Tapeout. docs/SPEC.md is frozen v0.1 and it is law. Live task state lives in TASK_LOG.md, never in this file. The working discipline is OPERATING_MANUAL.md v2 at the vault root, indexed below.

## Directive index, section numbers point into the manual

1. Read TASK_LOG.md first, re verify mutable facts by the cheapest check. Manual 1.
2. Pass or fail acceptance criteria before acting, prompt re read clause by clause at the end. Manual 2.
3. Hard stops, spec ambiguity, frozen docs, destructive actions. Proceed only on cheap to reverse calls. Manual 3.
4. Freeze the contract, cut units with exit checks, one commit per unit, baseline first. Manual 4.
5. Verify identifiers, APIs, and tool behavior this session, report claims at their evidence level. Manual 5.
6. Adversarial review with mutation is the primary gate, the risk map only seeds review dimensions. Manual 6.
7. One home per fact. Log at every unit. Loop breaker after two identical failures. Manual 7.
8. Report failures as failures with output, run the final gate. Manual 8.

## Repo facts

- Layout. src holds four modules. tb holds two suites plus golden.py and the dumpers. docs holds SPEC.md, frozen, and SPEC_NOTES.md, the v0.2 queue, not in force.
- Run. source ~/.venvs/mac8/bin/activate, then cd tb and make. Single suite, make TB=datapath or make TB=top.
- Lint. verilator --lint-only -Wall --top-module mac8_top src/*.sv, must stay clean.
- The venv stays outside the vault and Makefile paths stay relative. The vault path has spaces and make breaks on them.

## Ratified design decisions, do not relitigate

- sel encoding, 00 low, 01 mid, 10 high, 11 reserved reads low.
- Busy is a register, high the cycle after a MAC accept. Commands during busy are dropped, not deferred.
- accept is combinational off ff2 and ff3, gated by armed. A registered accept breaks the 2 to 3 clock contract.
- After reset the first command needs strobe observed low, then a fresh rise.
- CLR wins on overlapped pulses, and the datapath guard $fatals on any overlap.
- cmd and ui_in cross clock domains unsynchronized. The spec driver rules make them quasi static at sampling.
- out_byte lags by one clock by design, uo_out is registered.

## Toolchain traps

- cocotb 2.0.1 needs Python 3.13 or lower. The venv is Python 3.12.
- Icarus $countones is broken, explicit sums only in checkers.
- $error cannot fail a cocotb test, $fatal aborts the sim.
- Delete sim_build_* before mutation runs, stale compiled sims pass silently.

## Style

Short sentences. Periods and commas only. No em dashes. No semicolons. Never use leverage, tapestry, foster, delve, seamless, robust, game-changer.
