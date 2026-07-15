# Task Log. P1 MAC8

Updated. 2026-07-13, after the operating manual v2 rewrite.

## Goal

Design and verify the int8 MAC block, then pass the P1 gates. Acceptance for the build phase.

- [x] Datapath RTL, lint clean, unit tested against a golden model.
- [x] Synchronizer, command decode, top level, lint clean, protocol tested.
- [x] Reset arming fix, no phantom command, no replay.
- [x] Both suites green. 9 datapath, 13 protocol, plus 9 pin only gate level.
- [ ] Waveform walk with Surfer, one full transaction by hand.
- [ ] Pre submission gate, freeze week. Full local precheck in the Nix shell, tt-support-tools precheck.py with Magic DRC and the pin and boundary suite, pinned PDK. The local KLayout DRC alone does not satisfy the local precheck requirement.
- [ ] Explain phase with Arnav, every file and number.
- [ ] Common FAQ and hard FAQ drills from the P1 note.
- [ ] Closed book replication gate.
- [ ] RTL freeze review with Dad.

## Now

Round three. Close the async latency dimension, formal proof preferred, exhaustive sweep as the concrete backstop, then the review paperwork. Held from round two, the rsz-corners adoption decision. Open after that, the pre submission Nix precheck in freeze week, the waveform walk, the remaining drills, the replication gates, RTL freeze with Dad.

## Reasoned event, 2026-07-15, one unverified dimension, not three bugs

The reviewer named the pattern. F2, the arm bit reading the metastable flop. F3, the lockout width eating a legal command. The reset release, the harness delivering an asynchronous rst_n the spec assumed synchronous. All three were found by reading, none by the bench, and all three live in the same place, the async latency range that deterministic simulation collapses to a point. Each synchronized edge resolves in 2 or 3 clocks, independently, and no test in the suite can make that choice vary. That is one unverified dimension, not three separate bugs. Fixing the third instance does not verify the dimension. This task verifies the dimension, a formal proof over all latency choices if the flow stands up, and an exhaustive enumeration of the latency grid in the testbench either way. After this, the class is closed by proof or by enumeration, not by the absence of the next counterexample.

## Gate result, the async latency dimension is closed, 2026-07-15

Both legs landed. The dimension that produced F2, F3, and the reset release is now verified by unbounded proof and by concrete enumeration.

Formal, Yosys 0.67 with yosys-smtbmc and z3, stood up locally this session. Harness formal/f_handshake.sv, the real mac8_sync and mac8_ctrl under test, unmodified, cmd held at MAC. The driver is constrained to every legal strobe per v0.4 with free timing choices, and the value ff1 samples on any transition cycle is a free variable, the resolution direction, rises and falls both. Four safety properties. Never more than one rise in flight. No accept without a pending rise, no doubles, no phantoms. No rise finds the previous unconsumed, no losses, the lockout never eats a legal command at any latency combination and any legal spacing. Busy never blocks a legal accept. BMC to depth 60 passed. Temporal induction closed at step 13, unbounded. Vacuity checked, asserting no accept ever happens fails as it must, the model produces real handshakes.

Enumeration, test_latency_grid in tb/test_top.py, latency forced per edge by phase placement, 0.1 ns before a sampling edge is fast, 2 clocks, after is slow, 3 clocks. Spacings 4, 5, 6, all four latency combinations, two base alignments, 24 cells, every cell matches prediction. Legal spacings 5 and 6, two accepts in all sixteen cells, no lost command anywhere. Spacing 4, below contract, resolution dependent as designed, slow then fast blocks at offset 3, one accept, the other three combinations pass, two accepts. Suite now 14 protocol tests, all green.

The class that was verified by reading is now verified by proof and enumeration both.

## Explanation page refreshed through round three, 2026-07-15

The Notion study page now matches the sealed state, verified against the repo at commit 6758caf before writing, every number checked against the report files. New module section 2e for mac8_rst_sync. Lockout section rewritten at width 3 with the worst alignment arithmetic. Incidents 7 and 8 added, the page teaches eight. New top level sections, the formal proof and the waivers, sections renumbered to ten. Metastability concept carries the current bound, the delta trace, and the droop corner. Spec section at v0.4 with the best effort row. Currency callout cites the sealed run and netlist hash. Six new hard FAQ entries, 24 total. Defense drill reconciled, the would not sign answer now signs with the named waiver and the named open, silicon correlation next tile. Stale token sweep clean, no old width, no old threshold, no old margin, no pre rename module name.

## Round three paperwork, findings first, 2026-07-15

Finding, the synchronized reset tree violates max transition at the ss corners. Item 7 asked to confirm it clean and it is not. net42, one branch of the rst_ff2 fanout, reads 0.899 ns at max_ss_100C_1v60 against the 0.75 limit, 0.860 at nom_ss, 0.811 at min_ss, 11 pins each, and one sink is _1563_/A, the reset AND on the ff1 to ff2 path. Exposure analysis, the net is static in operation and transitions once per reset, the side input slew does not enter the B to X arc delay the MTBF slack uses, and every reset release timing path is met. The rsz-corners branch improves it only to 0.892, same class, no clear. Folded into the waiver as class 2, not stated away. All other corners clean, and the tt corners carry no reset tree violations.

Checked and closed. A suspected discrepancy in the STA table dissolved on inspection, the doc's t 17.544488 is correct for run 29401092054, the competing 17.570266 came from the intermediate run 89dd70f, my own cross run comparison error, the doc stands. The reset synchronizer flops are the same dfxtp_2 cell as the strobe flops, instances _1636_ and _1635_, scope stated in the CDC doc, one event per reset, outside the f_data rate model. The ss extraction is already at the low supply corner, 1.60 V, 11 percent below nominal, board droop priced, no refit needed, tau unchanged. t carries the 0.25 ns clock uncertainty, stated. f_data stated as an input assumption, 10 MHz worst legal, linear in the denominator. The threshold delta trace is written, 353.77 to 351.04 ps decomposes as plus 1.76 from the slack move at commit 49f5f29, the reset path re placement, minus 4.49 from the conservative T0 promotion, the refit moved nothing, the CSVs and fit are unchanged.

Timing annotated gate level, added, item 8. Icarus with the sky130 timing models, gspecify, and the max_ss_100C_1v60 SDF from the final run annotated onto the netlist, verified applied by the missing file probe, Icarus warns on a bad path and stayed silent on the real one. All 9 pin tests pass annotated, through the power up X window, every reset test covering the flop init. Tooling committed, test/Makefile.sdf and test/sdf_annotate.v, the SDF itself stays an artifact of run 29401092054, path recorded, not committed.

Spec v0.4 lockout row rewritten as best effort, resolution dependent below the legal spacing, slow then fast blocks and the rest pass, reconciled with the prose, pinned by test_lockout_boundary_gl and test_latency_grid, changelog notes it as wording only. The waiver W1 is written at docs/WAIVERS.md with magnitudes, named corners, arcs, the 1.556 ns downstream slack through the waived nets, max cap clean at all nine corners, the adverse sign extrapolation bound, and the priced fix branch. README gained the netlist hash, the seal boundary sentence, the formal row, and the waiver pointer, and the repo description is set. The reset minimum reached the datasheet surfaces, docs/info.md had it and info.yaml description now carries it.

## Round two follow ups, slew classification, constraint audit, X window, 2026-07-15

Slew violations classified, final run 29401092054. The 33 at max tt are three datapath nets, u_dp.b_q[2] behind fanout52, u_dp.a_q[2] behind fanout65, and the multiplier internal net _0082_ behind the fanout20 chain, operand register fanout into the multiplier array. Every violation is within 8 ps of the 750 ps limit, about 1 percent. Not clock, not reset, not scan, not the synchronizer. Zero sync pins in the violator list, and the sync path slews from the same corner reports are ff1 CLK 53.3 and ff2 D 38.5 ps at max tt, ff1 CLK 82.3 and ff2 D 68.8 ps at max ss, 9x inside the limit. The earlier 76 and 69 ps figures were the prior run 89dd70f, same scale.

Precheck does not gate on max transition. The final run precheck report lists 15 checks, Magic DRC, six KLayout decks, pin, boundary, power pin, layer, cell name, urpm nwell, analog pin, Verilog syntax. All geometry, connectivity, and naming. All 15 green. No timing check exists in the precheck.

Resizer experiment, branch rsz-corners, commit 3cbf169, run 29404662777, all jobs green including precheck. RSZ_CORNERS set to nom tt, max tt, max ss, min ff. Result, partial reduction, not a clear. Slew 254 to 214 at max ss, 33 to 22 at max tt, nom tt cleared to 0. Setup improved at every corner, max ss 1.556 to 1.934 ns. Hold unchanged, worst 0.1108 vs 0.1106. Cells 1191 vs 1188, utilization 64.07 vs 63.95. The remaining 214 are the same operand fanout class, worst pin 1.214 ns, unchanged. Mechanism, repair runs at placement and global route, RUN_POST_GRT_RESIZER_TIMING is False, no post route repair pass exists, and detailed route parasitics at ss exceed the limit again. Clearing fully needs post route repair or a stronger operand fanout strategy, a bigger PPA move. Adoption held for Arnav, it would also re baseline the one hash package for a partial improvement.

Setup jump signed. The old run 29314372443 and the final run have byte identical signoff SDC, and across the entire resolved flow config exactly one key differs, VERILOG_FILES, the added mac8_rst_sync.sv. Clock period 20 ns, uncertainty 0.25, clock transition 0.15, IO delay 20 percent, derate 5 percent, max transition 0.75, all identical. Both worst setup paths are the same reg to reg class, operand register through the multiplier into the accumulator, a_q[7] to acc_q[8] at plus 0.695 in the old run, b_q[3] to acc_q[22] at plus 1.556 in the final. The improvement is re synthesis and re placement of the same path class, seeded by the F3 logic change and the added module. No constraint moved. Signed.

rst_n synchronizer survival confirmed. rst_ff1 is _1636_, rst_ff2 is _1635_ in the final netlist, two distinct dfxtp_2 flops, one driver each, hold82 between them, neither merged nor swept. GL netlist flops power up X, proven at the source, reg Q uninitialized in the dff primitive, primitives.v line 209. GL suite rerun locally on the powered final netlist, 9 of 9, through the power up X window, matching CI. Reset length audit, start_and_reset holds 4 clocks, the strobe high across reset tests hold 3, all at or above the 3 clock floor. Two mid operation reset pulses hold 2 clocks, test_reset_replay and test_in_flight_cancel, equal to the 2 clock settle, below the 3 clock driver floor, both pass at RTL and GL as deliberate sub floor probes. No test holds reset shorter than the settle.

## Verified facts, final hardened run, round two, 2026-07-15

- Run 29401092054 at commit 49f5f29, all jobs green, gds, precheck 15 of 15, gl_test 9 of 9, docs. Final netlist sha256 5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0. One run feeds every package table, CDC_MTBF, HOLD_REPORT, FANOUT_FF1, README.
- Std cells 1188, utilization 63.95 percent. Setup WNS plus 1.556 ns at max ss, TNS 0 everywhere. Hold WNS plus 0.111 ns at the fast corner, TNS 0, nine corners. Magic DRC 0, LVS 0, antenna 0. Hold buffers 19, up from 12.
- Slew wart evolved. 254 max slew violations at max ss, worst 1.207 ns against 0.750, and now 33 at max tt, 11 at nom tt, which were zero before round two. Zero fanout violations. Setup and hold met everywhere, still the deferred resizer call.
- Sync integrity on the final netlist. ff1 _1624_, ff2 _1625_, ff3 _1626_, rst_ff1 _1636_, rst_ff2 _1635_, five distinct dfxtp_2, one driver each. ff1 Q drives exactly the hold buffer, rst_ff1 Q drives exactly its hold buffer, evidence in docs/FANOUT_FF1.md.
- ff1 to ff2 setup slack 18.679211 ns at nom tt, 17.544488 ns at max ss. Hold 0.740827 and 1.753611. The bound recomputed on the conservative pair with the final t, threshold 351.04 ps, margin 2.62x over the headline tau 134.19 ps.

## Round two closed, deltas against the reviewer text, 2026-07-15

Reported, not silently fixed. The review said accepts can land 2 apart, the correct worst legal spacing is 4, the fix is the same. The review quoted threshold 349.3 ps and margin 2.60x, computed on the pre fix slack 17.458 ns, the final run reads t 17.544 ns, threshold 351.04 ps, margin 2.62x. The review ballparked the sensitivity rows at about 1e25 s at 2x and about 4e10 s at 4x, those verify on the combined pair with the old t, the doc carries the conservative basis with the final t, 2.1e24 s and 1.3e10 s, about 426 years, plus the 3.3x Beer and Ginosar row at about 437 thousand years. README written, it was the Apache license before. Hold report regenerated from the final run, the old one cited 29314372443 while the CDC doc cited 29352875225, the exact two run mismatch the review flagged.

## Reasoned event, 2026-07-15, F3 lockout width drops a legal command, review only catch

Round two review found it, and it is the sharpest catch yet. accept fires 2 to 3 clocks after the external edge, per edge, independently, because ff1 resolution direction at the sampling boundary is random per event. Two legal rises at the 5 clock minimum spacing can land their accepts 4 clocks apart, first resolves slow at plus 3, second fast at plus 2. The lockout as built sets locked at the end of the accept cycle and holds it while lock_cnt runs 0 to 3, so accepts at offsets 1 through 4 are blocked. Offset 4 is a legal command. The lockout eats it.

No deterministic simulation can see this. Sim collapses the 2 to 3 latency range to a point, two in phase edges resolve identically, accepts land 5 apart, the window never bites. Same blind spot class as F2 metastability. Caught by review, closed by width proof, not by simulation.

One arithmetic correction against the review text, reported, not silently fixed. The worst legal accept spacing is 4 clocks, not 2. Latency jitter is at most 1 clock, so 5 minus 1 is 4. The fix is identical either way. Terminal 2'd2, a 3 clock window, blocks offsets 1 through 3, passes offset 4. Ring coverage holds, the earliest second synchronized edge from one physical strobe needs ff2 low for a cycle, offset 2, inside 3. Any later re crossing violates the high 3 low 2 pulse shape and is a second pulse, out of contract.

A consequence found while re deriving the ring arithmetic. The old GL ring test drove a bounce with rises 4 clocks apart, which the old window blocked and the new window passes by design. The pattern tightened to rises 3 apart, and the rewritten lockout test pins the exact window edges in deterministic sim, offset 3 blocked, offset 4 passes, offset 5 passes. The offset 4 row kills a mutation reverting the window to 4. Mutation runs, revert to 2'd3 fails the offset 4 row, lockout removed fails both ring tests. Both killed.

## Reasoned event, 2026-07-15, rst_n is asynchronous at the pad, two sources

The round two rst_n question resolved against the easy path. The Tiny Tapeout clock spec states, both the clk and rst_n pins are handled like any other input pins, source tinytapeout.com/specs/clock, file content/specs/clock/_index.md in the tinytapeout_www repo. The harness RTL confirms it, tt-multiplexer rtl/tt_user_module.v.mak line 53, assign uio_in ui_in rst_n clk equals iw, the user rst_n arrives in the same input bundle as ordinary inputs, no synchronizer in the spine. So the spec's old line, deassert treated as synchronous, was an assumption the harness does not back.

Fix per the ruling. mac8_rst_sync, two plain flops with keep, no reset on themselves, instantiated in the top, no module sees the raw pad. Assertion and release reach the core 2 clocks after the pad. Driver counts moved in spec v0.4, hold rst_n low at least 3 clocks, hold strobe low at least 5 clocks after release, the derived hard floor is 3. This class is review driven, deterministic sim cannot express an async reset edge race, same blind spot as F2 and the lockout width. Reset release happens about once per session, so the MTBF of this crossing sits far beyond the strobe path bound. start_and_reset and the GL reset boundary probe updated to the new counts, in flight cancel docstring updated, the command can execute inside the 2 clock crossing window and is then wiped, identical through the pins.

## Extraction hardening, round two items 7 to 9, 2026-07-15

Provenance first, a real finding. The extracted cell file dfxtp_2.spice was never committed and no longer existed on disk, the deck hash pinned a path string, exactly the reviewer's attack. Re extracted from the PDK, 28 lines, committed at docs/cdc/dfxtp_2.spice, sha256 26e32b3c4f62819c2253c4ebded610e5a6a9faca3c68875c5820c364c1551632. PDK source sky130_fd_sc_hd.spice sha256 6dec6626decd1ee15afacafab9925b1a336ab344b7b5e1bec9d7483f2a6badc3, volare, open_pdks c6d73a35.

Slew rerun, item 7. Real stimulus slews pulled from the hardened netlist STA, ff1 CLK 75.907 ps and D 69.337 ps at ss, in place of the 20 ps convenience edges. Combined tau 131.49 to 131.02 ps, 0.4 percent. T0 12.42 to 16.25 ps, inside a log. Sweep committed, sweep_ss_0fcc822d.csv. tau does not depend on convenient stimulus.

Solver check, item 9. reltol 1e-7, max step halved to 0.25 ps, trap for gear. Combined tau 131.42 ps, under 0.1 percent from baseline. Sweep committed, sweep_ss_f6bb1d1f.csv. Physics, not integrator artifact.

meta_bench.py gained env overrides for edges and solver, defaults reproduce the original decks byte for byte. Worst per side tau across all three ss runs stays 134.19 ps from the baseline, the conservative headline pair holds.

## MTBF argument placed, 2026-07-14

Nav delivered the spoken MTBF argument paragraph. Placed verbatim into docs/CDC_MTBF.md under the heading MTBF for the strobe synchronizer, replacing the placeholder. No rewording, it is his.

Verified every number independently before placing. Test count gate first, 22 white box, 9 datapath and 13 protocol, plus 9 gate level, matches the paragraph. The 14th cocotb decorator grep hit is a comment line, not a test. Recomputed the bound from scratch. D 6210 per second from T0 12.42 ps times 50 MHz times 10 MHz. ln(A times D) 49.348. Threshold 353.77 ps at the exact t 17.457877 ns, 353.8 ps at the paragraph rounded 17.46 ns. Ratio 2.690 over extracted ss tau 131.49 ps. Reran scripts/fit_tau.py, tt tau 42.80 T0 20.17, ss tau 131.49 T0 12.42, matches the paragraph rounding. Doubling T0 moves the threshold 1.39 percent, inside the paragraph's about 1 percent. No number disagreed.

Marked the deliverable complete, frontmatter status, intro flag, and a new deliverable table row. Surfaces mirrored as status flips only, not the prose, the Obsidian fit note, the P1 note, and the Notion build log.

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

## Verified facts, F1

- Hardening numbers, from runs/wokwi/final/metrics.json of CI run 29308958917 at commit ca13138. Std cells 1181, sequential 61, total instances 3015 with fill and tap. Utilization 63.7 percent. Core area 16493 um2, die 17955 um2, fits 1x1. Setup WNS plus 0.695 ns at the worst corner, ss 100C 1v60 max, TNS 0 everywhere. Hold WNS plus 0.111 ns at ff n40C min, TNS 0. Magic DRC 0, KLayout checks clean, LVS 0, antenna 0.
- 263 max slew violations at the ss 100C 1v60 corner only, worst 1.06 ns against a 0.75 ns pin limit, zero at tt and ff. Setup and hold still met. Flagged for round two review.

## Metastability fit and bound, 2026-07-14

Fit done, scripts/fit_tau.py, numpy polyfit on x equals ln(1 over offset), slope is tau, T0 equals exp(intercept over tau), relation stated in the script comment. tt tau 42.80 ps, T0 20.17 ps. ss tau 131.49 ps, T0 12.42 ps. Sanity gate passed, tt tau in the tens of ps band, proceeded.

Finding, combined R squared reads 0.88 at both corners but per side fits are 0.998 to 0.999 with slopes agreeing within 5 percent. The penalty is branch asymmetry, the two resolve directions carry different T0, not nonlinearity. The model holds.

Threshold derived at the signoff corner, ss. t 17.457877 ns from the STA table, f_clk 50 MHz, f_data 10 MHz worst legal, T0 12.42 ps. D 6210 per second, ln(A times D) 49.348, threshold tau 353.77 ps. Margin 2.69x over extracted ss tau, 2.64x against the worst per side value, and doubling T0 only moves the threshold to 349.30 ps. Values written to docs/CDC_MTBF.md under Extraction and bound, deliverable table at the top, MTBF argument heading left as a placeholder for Nav.

Teaching written two tier, with and without background, vault note Chip Design Track/Projects/MAC8 Metastability Fit.md and Notion child page Metastability Fit under the build log. Replication gate written, docs/cdc/REPLICATE.md, thirteen boxes closed book.

## Round 1.5 follow up, keep attributes and bench refinement, 2026-07-14

Keep ruling applied. keep on ff1 ff2 ff3 in the RTL only, hold fixing untouched, no dfrtp, sync reset stands. Flow rerun 29352875225 at e82437b, all jobs green. Netlist re verified, three distinct dfxtp_2 instances, one driver each, no merge, no replication. Full ff1 to ff2 path, _1614_ dfxtp_2 Q, u_sync.ff1 net, hold90 dlygate4sd3_1, net90, _1553_ and2_2 with rst_n on the A pin, _0053_, _1615_ dfxtp_2 D. Every baseline metric identical to the pre keep run, cells 1181, util 63.7 pct, setup WNS 0.695, hold WNS 0.111, slew 263, DRC LVS antenna 0, GL 9 of 9.

STA extraction done, docs/CDC_MTBF.md created, values only under STA traceable inputs. ff1 to ff2 setup slack 18.632 ns at nom_tt, 17.458 ns at max_ss. Hold slack 0.789 and 1.840 ns. The derivation body stays pending Arnav's paste, status draft, tau and T0 pending sourcing.

Bench refined per item 4. Probes the master latch storage node xdut.a_466_413#, chosen because the master cross coupled pair is a_466_413# and a_634_159#, the input tgate writes a_466_413# on CLK low and the clocked feedback holds it after the rising edge, so the dwell lives there. Q sits behind the slave tgate, an inverter, and the output buffer, which regenerate and hid the dwell, the flat column of the first sweep. Grid ladder locates the balance to sub fs, tt at 4.976707125 ns with a 5 ns clock edge. Log spaced fs offsets both sides, tight reltol 1e-6 abstol 1e-15 gear, single session per grid. tt sanity band passes, resolution grows as offset shrinks, about 0.10 ns per decade, 0.106 ns at 1000 fs to 0.467 ns at 1 fs. No tau fit, no T0, no MTBF text, those are Arnav's.

## F1.5 reviewer round, 2026-07-14, results

Item 2, GL directed set. Three directed pin only tests added, all off grid. test_reset_release_strobe_high_gl, hold strobe high across reset plus one and plus two clocks, zero accepts proven by an A corruption probe. test_lockout_boundary_gl, a second rise 4 clocks after the first is ignored, one MAC, at 5 clocks accepted, two MACs, read via acc. test_data_hold_window, data captured in the window, a change past the hold boundary ignored. All three run on the hardened netlist in CI, gl_test 9 of 9 on run under commit 07137e0. These are the classes synthesis reintroduces, now pinned on the netlist.

Item 3, hold report. docs/HOLD_REPORT.md, nine corners. Worst hold slack plus 0.111 ns at min_ff_n40C_1v95, the fast corner. Hold TNS zero at every corner. Met, thin at the fast corner.

Item 4, reset polarity. docs/info.md now maps rst_n from the harness through the wrapper to every module, active low, synchronous, no inversion at any step. The sync reset shows in the netlist as an AND on each flop D, which is why the flops are dfxtp not dfrtp.

Item 5, spec v0.3, both copies identical. Two driver rules became stated interface requirements with violation behavior and a pinning test each. Rise to rise 5 clock minimum, pinned by test_lockout_boundary_gl. Data setup and hold, pinned by test_data_hold_window, a new test written for it.

Item 6, local precheck. Ran the sky130A KLayout DRC deck locally, feol beol offgrid enabled, 256 rule categories, 0 violations, the GDS is DRC clean on this machine. Command, klayout -b -rd input=GDS -rd top_cell=tt_um_arnav_mac8 -rd feol=true -rd beol=true -rd offgrid=true -r sky130A_mr.drc, PDK from volare. The full shuttle precheck also runs Magic DRC and a pin and boundary and cell name suite inside a Nix shell with a pinned PDK version, which I did not stand up locally. CI runs the full precheck green, 15 of 15 checks on the shipped run. So the core geometry check is confirmed locally, the rest is the container flow, green in CI.

Item 7, metastability bench. docs/cdc/, the bench for ff1, the dfxtp_2 cell from item 1. Structure per Beer and Ginosar, fixed clock edge, swept D edge time, find the capture balance, log Q resolution against offset. Built single session, models parse once then a control loop reruns the transient per point, 141 points in about 95 seconds, versus 43 seconds per point when each run reparsed the models. Tools installed for this, ngspice via brew, sky130A PDK via volare. Sanity sweep at tt converges, balance at td 19.9765 ns, the captured value flips cleanly there, 1 before the balance, 0 after. Honest limit, the resolution time reads at the floor across the plus and minus picosecond offsets, so the metastable window at tt is under 1 picosecond at that precision. The fine resolution tail needs a femtosecond zoom and tighter solver handling, which fought convergence without uic in this session. Per the instruction the tau fit, the plot, and the MTBF paragraph are Arnav's, so the bench is the framework and the located balance point, not the tail. No tau fit, no MTBF text written.

Cell for item 7, a flag. The reviewer said use the cell from item 1, not the generic dfxtp. Item 1 found dfxtp_2, which is the generic dfxtp, because ff1 is a sync reset plain flop, not the dfrtp the reviewer predicted. So the bench correctly characterizes dfxtp_2, the real ff1 cell, and the not dfxtp instruction was based on the async reset prediction. Named here so the reviewer can confirm.

## Finding, synchronizer netlist integrity, 2026-07-14, blocking, item 1 stopped

Grepped the hardened netlist, run 29314372443 on main. ff1 is instance _1614_, ff2 is _1615_, ff3 is _1616_, all sky130_fd_sc_hd__dfxtp_2. Not dfrtp. The reviewer predicted dfrtp assuming async reset. Our reset is synchronous, ratified, so synthesis used a plain flop and folded the reset into the D logic. dfxtp is the correct mapping for sync reset.

Core integrity holds. Two distinct instances for ff1 and ff2, one each, no merge, no replication. But not directly connected. ff1 Q has one load, a hold fix delay cell hold90, dlygate4sd3_1. Its output feeds and2_2 _1553_, the synchronous reset gate, ff2 D equals ff1 delayed AND rst_n. So two cells sit between ff1 and ff2, the reset AND by design, and a tool inserted hold buffer.

Per the reviewer's gate, anything inserted is a blocking finding, so I stopped item 1, no keep attributes added, no rerun. The reset gate is unavoidable with sync reset. The hold buffer is benign for MTBF, the resolution window is about 20 ns and the buffer eats a fraction of a ns, but it is a real CDC hygiene smell and keep alone will not remove it. Proposed fix for the reviewer to approve, add keep on ff1 ff2 ff3 to lock against merge and replication, and exclude the ff1 to ff2 net from hold fixing, or move the sync flops to async reset dfrtp so the path is direct. Not applied, awaiting the ruling.

## Finding 2 fix attempt, 2026-07-14, reverted, blocked on reviewer

Tried the sanctioned lever, DESIGN_REPAIR_MAX_SLEW_PCT raised from 20 to 50, spending from the setup margin not the clock. It failed both ways. Setup broke, WNS went plus 0.695 to minus 0.530 ns at ss 100C 1v60, TNS minus 4.784, so 50 MHz no longer closes at the worst corner. And the slew count did not drop, still 263 at max ss, worse at min and nom ss. The margin knob repairs at the typical corner, these violations are at the slow corner, wrong lever. CI still went green because the flow does not fail on a slow corner setup violation, a vacuous green, caught by reading the metrics. Reverted config.json byte identical to the baseline, commit 472c1bf, confirmed setup plus 0.695 restored, slew 263, GL 6 of 6.

The slew stays open, a signoff wart, not a flow error. The real lever is RSZ_CORNERS set to include ss 100C 1v60 so the resizer repairs slew at that corner directly, which costs area or setup margin, a PPA call for the reviewer. Not applied, the instruction was margin knobs then stop and report. Question for round two, accept the slow corner slew as is, or authorize RSZ_CORNERS and spend the area.

## Render, 2026-07-14

Two GDS shots in docs/, gds_full_die.png and gds_cell_rows.png, embedded in info.md, combined 412 KB, under the TT datasheet limit. The full die is the flow's own KLayout render, real sky130 colors. The zoom is a standalone klayout pymod render, monochrome. These are 2D layout renders, not the interactive 2.5D perspective. The macOS KLayout cask app cannot render headless, its Qt build is cocoa only with no offscreen plugin, so the GUI 2.5D view was not scriptable inside the time box. The pymod path rendered offscreen, no PDK color file was available locally to colorize the zoom.
- GL suite 6 of 6 on the hardened netlist. It caught nothing RTL sim missed, the X out of reset class was the risk and the reset path held.
- Doc cross check, mechanical plus two adversarial agents. Pin tables identical to SPEC character for character, all 24 yaml labels match. Two real doc bugs found and fixed, the GPIO count said 12 where the enumeration totals 22, and the busy drop rule was missing from info.md.
- The template Makefile broke locally on the vault path spaces, fixed with relative paths, the standing trap.

## Verified facts, review batch

- Both suites green after every unit. 9 datapath, 13 protocol, verified by make.
- Empirical min strobe low time for the first post reset arm is 1 clock hard floor, 3 clocks safe. Verified by a low time sweep, k=0 gives 0 accepts, k>=1 gives 1.
- Arming off ff2 adds no shift to any test expectation. Verified, the three reset tests and the latency and busy tests all pass unchanged.
- Lockout catches the ringing edge. Verified, mutation removing the lockout fires 2 MACs on the ringing test.
- Phase randomization is sub cycle, so edge count assertions hold. Verified, both suites green with the Timer offset on every strobe.

## Vault infrastructure, 2026-07-13

The vault itself is under git now, remote github.com/Arnav66692/chip-design-track-vault, private. code/ is ignored there, mac8 stays its own repo and pushes independently, verified. Session end sync includes a vault commit and push. Git is the history layer under the homes, not a new home.

Manual disappearance investigation, closed. Mechanism confirmed, the original v2 inode is gone, the restored file's birth time is 15:16. Both Trash locations empty, no Spotlight remnant, no third copy on disk. The Claude-Project-System folder is intact minus exactly the one file deleted on record after a byte identity check, so the wrong path theory fails. Window, 12:52 to 15:16. Cause unknown, and the git layer makes recurrence a one checkout recovery.

## Finding, v2 manual was missing from disk

At F8 the vault OPERATING_MANUAL.md, the v2, was gone. Only OPERATING_MANUAL_v1.md remained, the original 34694 byte Fable 5 handoff. My conversation memory said v2 was written and edited, disk said otherwise, and the manual says trust the disk. The CLAUDE.md pointers to v2 were dangling. Cause unknown, the explanation and iCloud tasks in between did not touch it. Since the F8 instruction presupposes the manual exists, I restored v2 faithfully from the authoring conversation, with the two prior audit fixes and the F8 line, and noted the restore in its changelog. If a process is silently removing vault files, that is the real risk, flagged for Arnav.

## Plan state

- [x] Datapath. Exit check, make TB=datapath, 9 green.
- [x] Sync, ctrl, top. Exit check, make TB=top plus verilator -Wall clean.
- [x] Reset arm bit. Exit check, 3 reset tests pass, arm gate mutation fails them.
- [x] Vault move. Exit check, both suites green from the new path.
- [x] Operating manual v2. Exit check, evidence audit of every cited hash and number, v1 archived, state files brought to one home per fact.
- [x] Manual audit fixes. Exit check, all five audit findings corrected, protocol suite 12 green after the cancel test hardening, commit a190b91.
- [x] F1 Tiny Tapeout integration. Template adopted into this repo from ttsky-verilog-template at the ttsky26c tag, confirmed via the live shuttle page and the template's own tag commit. Top renamed to tt_um_arnav_mac8, not wrapped. Pin only suite in test/ runs at RTL and gate level, white box stays in tb/. Exit check, gds, precheck, and gl_test jobs green in CI, 6 of 6 GL tests pass on the hardened netlist, fits 1x1 at 63.7 percent utilization, setup and hold met at all corners. Viewer job disabled, Pages needs a public repo. KLayout render skipped, not installed, would blow the time box.

## Verified facts

- Both suites green. Verified by make, 9 datapath plus 12 protocol, this session.
- Arm bit adds no latency. Verified, test_accept_latency_two_to_three still passes.
- $fatal aborts the sim. Verified by a scratch double pulse sim, it never reached the end marker.
- Icarus $countones returns 6 for a two bit concat. Verified by a micro sim. Guard uses an explicit sum.

## Decisions

- Reset arming by arm bit, ruling from Arnav. All flops still clear on reset.
- Guard uses $fatal not $error, so an overlap actually fails a run.
- Lockout stays as built, 4 clocks via a 2 bit counter plus a run flag. Ratified, the 2 bit counter clause was a cost estimate, not a requirement.
- Vault spec copy renamed to MAC8 Spec.md, version neutral, the version lives inside the file. Zero hand maintained references needed fixing, verified by sweep.
- Notion Explanation page refreshed to the current repo, 2026-07-13. It now carries the ff2 arm with the two cycle skip, the F3 lockout section, the spec v0.2 rules, incidents five and six, and four new hard FAQ. Marked current as of ba49d54. Verified by refetch, 28 checks, 63 toggles, no stale strings outside the one labeled historical quote.

## Dead ends

- $error in the guard. Prints under cocotb but cannot fail a test. Replaced with $fatal.
- $countones in the guard. Broken under Icarus. Replaced with an explicit sum.

## Open questions

- MTBF analysis, a gate list item from the design review. Status, drafted. Arnav derived it closed book, see the vault drill log. Placement into docs/CDC_MTBF.md and independent verification of every number are next, content arriving. Blocked on sourcing real sky130 tau and T0 from the standard cell characterization data. That sourcing is a question for the reviewer.
- SPEC_NOTES.md holds the v0.2 queue, driver rule clarification and fused LDB_MAC. Not blocking.

## Resolved, repo location, 2026-07-13

Ruled by Arnav. The repo stays inside the vault at code/mac8. His earlier claim that a prior ruling said code stays out was false, there was no such ruling, correction noted here as instructed.

iCloud finding, with evidence and method. The vault is not iCloud Drive synced on this Mac. Verified four ways. ls ~/Library/Mobile Documents returns No such file or directory, the iCloud Drive container does not exist. fileproviderctl dump reports the iCloud Drive domain last drop reason Domain disabled. brctl status self check fails access denied. Zero .icloud placeholder files anywhere in the vault. The account has CloudDesktop provisioned but the Drive domain is off on this machine, so nothing syncs the .git directory. Recheck cheaply with ls ~/Library/Mobile Documents, if it exists, iCloud Drive is back on and the git exclusion decision reopens.

Protections applied. Obsidian exclude filter, .obsidian/app.json userIgnoreFilters holds code/, so the vault stops indexing the repo. No git internals exclusion needed, iCloud is off. GitHub is the real backup, origin set to github.com/Arnav66692/mac8, working tree clean, nothing unpushed.

## Files touched this project

- src/, all four modules. tb/, both suites plus golden.py and dumpers. docs/SPEC.md and SPEC_NOTES.md.
