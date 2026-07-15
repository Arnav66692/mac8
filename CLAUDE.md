# mac8

Int8 serial MAC for Tiny Tapeout. docs/SPEC.md is frozen and it is law, the version lives inside the file. Live task state lives in TASK_LOG.md, never in this file. The working discipline is OPERATING_MANUAL.md v2 at the vault root, indexed below.

## Directive index, section numbers point into the manual

1. Read TASK_LOG.md first, re verify mutable facts by the cheapest check. Manual 1.
2. Pass or fail acceptance criteria before acting, prompt re read clause by clause at the end. Manual 2.
3. Hard stops, spec ambiguity, frozen docs, destructive actions. Proceed only on cheap to reverse calls. Manual 3.
4. Freeze the contract, cut units with exit checks, one commit per unit, baseline first. Manual 4.
5. Verify identifiers, APIs, and tool behavior this session, report claims at their evidence level. Manual 5.
6. Adversarial review with mutation is the primary gate, the risk map only seeds review dimensions. Manual 6.
7. One home per fact. Log at every completed unit, dead ends never deleted. Manual 7.
8. Reports lead with findings, green checkmarks last. Report failures with output, run the final gate. Manual 8.
9. Untested policy, the loop breaker and request classification, labeled and cheap, delete on first failure in use. Manual, Untested policy section.

## Repo facts

- Layout. src holds four modules, the top is tt_um_arnav_mac8, was mac8_top before F1. tb holds the two white box RTL suites plus golden.py and the dumpers. test holds the Tiny Tapeout pin only suite. docs holds SPEC.md, frozen, version inside the file, SPEC_NOTES.md the feature queue, and info.md the shuttle datasheet source.
- Run. source ~/.venvs/mac8/bin/activate, then cd tb and make. Single suite, make TB=datapath or make TB=top.
- Lint. verilator --lint-only -Wall --top-module tt_um_arnav_mac8 src/mac8_*.sv src/tt_um_arnav_mac8.sv, must stay clean. src/config.json is the TT hardening config, not RTL.
- Tiny Tapeout. Workflows in .github/workflows are verbatim from ttsky-verilog-template at the ttsky26c tag. test/ is the pin only suite, runs at RTL and gate level in CI. tb/ is the white box RTL suite, local only. Do not submit to the shuttle, that is Arnav's decision.
- The venv stays outside the vault and Makefile paths stay relative. The vault path has spaces and make breaks on them.

## Ratified design decisions, do not relitigate

- Repo location, code/mac8 lives inside the vault, ruled 2026-07-13. The vault is not iCloud Drive synced on this Mac, so .git is not at sync risk, recheck with ls ~/Library/Mobile Documents. Obsidian excludes code/ via the vault .obsidian/app.json. Evidence in TASK_LOG.
- sel encoding, 00 low, 01 mid, 10 high, 11 reserved reads low.
- Busy is a register, high the cycle after a MAC accept. Commands during busy are dropped, not deferred.
- accept is combinational off ff2 and ff3, gated by armed. A registered accept breaks the 2 to 3 clock contract.
- After reset the first command needs strobe observed low, then a fresh rise.
- CLR wins on overlapped pulses, and the datapath guard $fatals on any overlap.
- Edge lockout, accepts ignored 3 clocks after any accept, built as a 2 bit counter plus a run flag. Width ruled 3 in round two, 2026-07-15, the 4 clock window ate a legal command at the worst async alignment, accepts from legal rises can land 4 apart. The 2 bit counter clause in the first review was a cost estimate, not a requirement.
- cmd and ui_in cross clock domains unsynchronized. The spec driver rules make them quasi static at sampling.
- out_byte lags by one clock by design, uo_out is registered.

## Toolchain traps

- cocotb 2.0.1 needs Python 3.13 or lower. The venv is Python 3.12.
- Icarus $countones is broken, explicit sums only in checkers.
- $error cannot fail a cocotb test, $fatal aborts the sim.
- Delete sim_build_* before mutation runs, stale compiled sims pass silently.

## Style

Short sentences, periods and commas only. The full rule with the banned word list is canonical in the vault root CLAUDE.md, one home per fact.
