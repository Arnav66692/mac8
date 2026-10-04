# MAC8 application verification matrix

This extends the baseline verification. Names identify executable checks,
not coverage percentages. All tests in verification/test_app.py observe
only external chip pins and use the production app/driver.py.

| Requirement | Check | Evidence and limit |
|---|---|---|
| Signed 8-bit multiplication | test_all_signed_operand_pairs | 65536 pairs in actual datapath RTL. White-box product observation, not a complete arithmetic proof. |
| Signed dot products and new B | test_signed_vectors_and_new_b | Extremes, mixed signs, changed B, empty vector and three-byte readback. Old-B and missing-MAC mutants fail. |
| FIR coefficient order and initial history | test_fir_impulse_step_and_alternation | Impulse, DC and alternating input against direct integer convolution. |
| Per-operation saturation and sticky flag | test_saturation_sticky_and_clear, test_seeded_command_soak | Both rails, continued MAC and CLR. Baseline exact rail landing checks remain in test/test.py. |
| Reset clears state and permits recovery | test_reset_recovery | Repeated complete pad reset. Baseline mid-strobe reset tests remain in test/test.py. |
| Busy output | test_busy_pin_contract | One cycle for ordinary MAC, two for fused MAC, zero for non-MAC, return to idle. Stuck-low busy mutant fails. |
| Setup, hold and byte read floor | test_command_hold_and_read_margin | Configured driver boundaries and conservative intervals. Existing phase-forced read test covers both synchronizer resolutions. |
| Arbitrary vectors | test_random_vectors | Fixed seed, lengths 1 through 511, signed reference. |
| Complete application and command cost | test_fir_demo_and_cycle_measurement | 128 outputs, bit-exact comparison and simulated time. Excludes host GPIO overhead. |
| Functional stress bins | test_seeded_command_soak | 100000 scheduled operations per RTL variant, fixed seed, all opcodes, both saturation rails, sticky clear, all byte selections and periodic reset. |
| Driver ownership | test_concurrent_transactions_are_rejected | Second concurrent public transaction fails before touching pins. One driver instance per device. |
| Interrupted transaction recovery | test_cancelled_command_requires_successful_reset | Cancellation during high strobe marks interface dirty. Next operation requires reset. |
| Host direction and GPIO ordering | test_demoboard_direction_and_delay, test_gpio_strobe_last | Mocked SDK ports and GPIO pins. Physical board execution remains unverified. |

## Formal boundaries

The original formal/f_handshake.sv proves selected command-acceptance
properties of mac8_sync and mac8_ctrl under its stated timing and startup
assumptions. It excludes the arithmetic datapath, data-bus correctness,
pad reset crossing and repeated-reset behavior. Its abstract delay model
does not measure physical metastability.

The candidate adds an independent scheduling proof in the FORMAL block
of experiments/fused/tt_um_arnav_mac8_fused.sv. BMC and induction establish
the pending transition, the following busy interval, one control pulse per
cycle and reset clearing. Reachability covers exercise fused acceptance
and its delayed MAC. Replacing pending reset with fused_fire fails BMC.
This is a control proof, not end-to-end arithmetic equivalence or a new
physical CDC signoff.

## Reproduce

```sh
python -m unittest app.test_reference
make -C verification -f arithmetic.mk
python scripts/check_results.py verification/results_arithmetic.xml --expect-from-tests verification/test_arithmetic.py
make -C verification VARIANT=baseline
python scripts/check_results.py verification/results_baseline.xml --expect-from-tests verification/test_app.py
make -C verification VARIANT=fused
python scripts/check_results.py verification/results_fused.xml --expect-from-tests verification/test_app.py
python scripts/check_app_mutations.py
python scripts/check_fused_control.py
```

Use the baseline README's virtual environment and installed Icarus,
Yosys and Z3 tools. CI runs the application, exhaustive multiplication,
mutation and candidate control gates. Filtered runs cannot pass the full
results gate because skipped testcases now fail it. The mutation runner
intentionally selects one test, verifies its active count, and uses fresh
isolated builds. A compiler or solver error is not a caught mutation.

The same application suite supports VARIANT=gate and VARIANT=fused-gate
with PDK_ROOT and the corresponding powered netlist in
test/gate_level_netlist.v. Gate results are labeled functional simulation.
The baseline's separately gated SDF flow remains its timing simulation
authority. Candidate routed STA is required before any timing claim.
