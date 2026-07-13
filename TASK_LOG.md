# Task Log. P1 MAC8

Updated. 2026-07-13, after the operating manual v2 rewrite.

## Goal

Design and verify the int8 MAC block, then pass the P1 gates. Acceptance for the build phase.

- [x] Datapath RTL, lint clean, unit tested against a golden model.
- [x] Synchronizer, command decode, top level, lint clean, protocol tested.
- [x] Reset arming fix, no phantom command, no replay.
- [x] Both suites green. 9 datapath, 12 protocol.
- [ ] Waveform walk with Surfer, one full transaction by hand.
- [ ] Explain phase with Arnav, every file and number.
- [ ] Common FAQ and hard FAQ drills from the P1 note.
- [ ] Closed book replication gate.
- [ ] RTL freeze review with Dad.

## Now

Implementing the design review gate list, F2 through F5 plus test upgrades. F1, the Tiny Tapeout integration, is its own task this week.

## Reasoned event, 2026-07-13, F2 is review driven not test driven

The review found a bug class the mutation gate is structurally blind to. The arm enable in mac8_sync reads ff1, the first synchronizer flop, which can go metastable. Only ff2 and later may feed logic. But Icarus does not model metastability, so no simulation can distinguish ff1 from ff2 in the arm enable, and no mutation can be made to fail. The fix is correct by review and by the synchronizer discipline, not by a passing test. The RTL comment says exactly this. This is the one gate tonight that the test suite cannot prove, and that is the point of naming it here.

## Plan state, review batch, all done

- [x] F2. Arm off ff2 not ff1, reset skip deepened to 2 cycles. Both suites green, arming lands one cycle later, no test expectation shifted. Commit 78240fb.
- [x] F3. Edge multiplicity lockout, 4 clocks after any accept, 2 bit counter plus a run flag. Ringing test one MAC, mutation off the lockout gives two. Commit 78240fb.
- [x] F4. Sub cycle phase randomization in command(), seed 20260713 logged, offset rounded to 0.1 ns for sim precision. Both suites green off the clock grid. Commit 46d4c49.
- [x] F5. Spec v0.2 frozen, both copies identical, read rule, reset rule, 50 MHz clock. Commit 11dddb0.
- [x] F6. Calendar swapped, review gate windows in the calendar and Home table.
- [x] F7. White box markers on every test and helper that reads internal hierarchy. Commit 964bf1e.
- [x] F8. Manual reporting line, reports lead with findings. Commit 7e5b8e3 for the index. Manual restored, see the finding below.

## Verified facts, review batch

- Both suites green after every unit. 9 datapath, 13 protocol, verified by make.
- Empirical min strobe low time for the first post reset arm is 1 clock hard floor, 3 clocks safe. Verified by a low time sweep, k=0 gives 0 accepts, k>=1 gives 1.
- Arming off ff2 adds no shift to any test expectation. Verified, the three reset tests and the latency and busy tests all pass unchanged.
- Lockout catches the ringing edge. Verified, mutation removing the lockout fires 2 MACs on the ringing test.
- Phase randomization is sub cycle, so edge count assertions hold. Verified, both suites green with the Timer offset on every strobe.

## Finding, v2 manual was missing from disk

At F8 the vault OPERATING_MANUAL.md, the v2, was gone. Only OPERATING_MANUAL_v1.md remained, the original 34694 byte Fable 5 handoff. My conversation memory said v2 was written and edited, disk said otherwise, and the manual says trust the disk. The CLAUDE.md pointers to v2 were dangling. Cause unknown, the explanation and iCloud tasks in between did not touch it. Since the F8 instruction presupposes the manual exists, I restored v2 faithfully from the authoring conversation, with the two prior audit fixes and the F8 line, and noted the restore in its changelog. If a process is silently removing vault files, that is the real risk, flagged for Arnav.

## Plan state

- [x] Datapath. Exit check, make TB=datapath, 9 green.
- [x] Sync, ctrl, top. Exit check, make TB=top plus verilator -Wall clean.
- [x] Reset arm bit. Exit check, 3 reset tests pass, arm gate mutation fails them.
- [x] Vault move. Exit check, both suites green from the new path.
- [x] Operating manual v2. Exit check, evidence audit of every cited hash and number, v1 archived, state files brought to one home per fact.
- [x] Manual audit fixes. Exit check, all five audit findings corrected, protocol suite 12 green after the cancel test hardening, commit a190b91.

## Verified facts

- Both suites green. Verified by make, 9 datapath plus 12 protocol, this session.
- Arm bit adds no latency. Verified, test_accept_latency_two_to_three still passes.
- $fatal aborts the sim. Verified by a scratch double pulse sim, it never reached the end marker.
- Icarus $countones returns 6 for a two bit concat. Verified by a micro sim. Guard uses an explicit sum.

## Decisions

- Reset arming by arm bit, ruling from Arnav. All flops still clear on reset.
- Guard uses $fatal not $error, so an overlap actually fails a run.

## Dead ends

- $error in the guard. Prints under cocotb but cannot fail a test. Replaced with $fatal.
- $countones in the guard. Broken under Icarus. Replaced with an explicit sum.

## Open questions

- SPEC_NOTES.md holds the v0.2 queue, driver rule clarification and fused LDB_MAC. Not blocking.

## Resolved, repo location, 2026-07-13

Ruled by Arnav. The repo stays inside the vault at code/mac8. His earlier claim that a prior ruling said code stays out was false, there was no such ruling, correction noted here as instructed.

iCloud finding, with evidence and method. The vault is not iCloud Drive synced on this Mac. Verified four ways. ls ~/Library/Mobile Documents returns No such file or directory, the iCloud Drive container does not exist. fileproviderctl dump reports the iCloud Drive domain last drop reason Domain disabled. brctl status self check fails access denied. Zero .icloud placeholder files anywhere in the vault. The account has CloudDesktop provisioned but the Drive domain is off on this machine, so nothing syncs the .git directory. Recheck cheaply with ls ~/Library/Mobile Documents, if it exists, iCloud Drive is back on and the git exclusion decision reopens.

Protections applied. Obsidian exclude filter, .obsidian/app.json userIgnoreFilters holds code/, so the vault stops indexing the repo. No git internals exclusion needed, iCloud is off. GitHub is the real backup, origin set to github.com/Arnav66692/mac8, working tree clean, nothing unpushed.

## Files touched this project

- src/, all four modules. tb/, both suites plus golden.py and dumpers. docs/SPEC.md and SPEC_NOTES.md.
