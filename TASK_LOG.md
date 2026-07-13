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

Build phase is done and green. Next working session is the explain phase, or the waveform walk with Surfer on tb/mac8_top.vcd. Arnav drives which.

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
