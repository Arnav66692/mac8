# probe_sel_boundary.py
# Contract evidence for the spec v0.5 read floor correction, cited from
# the SPEC.md changelog. Not part of the CI suite, on purpose. The stale
# read it demonstrates rides the clk to Q race at the old 4 clock floor,
# which is corner dependent, so a CI assertion on it would be fragile.
# The CI pinning test for the ruled 5 clock floor is test_sel_read_floor
# in test.py. Pin only, phase swept.
#
# The v0.4 read rule said sample uo_out no earlier than 4 clocks after
# the SEL strobe rise, derived as 3 clocks for the sync path plus 1 for
# the registered output. In the slow resolution alignment the output
# register launches the fresh byte at that same 4 clock mark, so the rule
# licensed sampling at the launch instant. This probe forces both
# synchronizer latencies per edge, the latency grid technique, a rise
# 0.1 ns before a sampling edge resolves fast, 0.1 ns after resolves
# slow, then samples uo_out at exactly the old floor. It reads stale in
# the slow alignment on the functional gate netlist and on the annotated
# netlist at max_ss_100C_1v60, and fresh one clock later, the v0.5 floor.
#
#   RTL         make COCOTB_TEST_MODULES=probe_sel_boundary
#   functional  make GATES=yes COCOTB_TEST_MODULES=probe_sel_boundary
#   annotated   make -f Makefile.sdf COCOTB_TEST_MODULES=probe_sel_boundary

import cocotb
from cocotb.triggers import ClockCycles, RisingEdge

from golden import Golden, apply_command
from test_top import (
    CLK_PERIOD_NS,
    CMD_LDA,
    CMD_LDB,
    CMD_MAC,
    CMD_SEL_LO,
    CMD_SEL_MID,
    STROBE,
    command,
    reset_only,
    start_and_reset,
    timer_ns,
)


@cocotb.test()
async def probe_sel_read_at_old_floor(dut):
    """Sample uo_out at exactly rise plus 4 clocks, the v0.4 floor, both
    latencies. On the gate netlist the slow alignment fails the assert,
    that failure is the demonstration this probe exists to reproduce."""
    await start_and_reset(dut)
    results = {}

    for slip, name in ((0, "fast, resolves in 2"), (1, "slow, resolves in 3")):
        await reset_only(dut)
        golden = Golden()

        # acc to 10000, 0x002710. Low byte 0x10 shows, mid byte 0x27 is
        # the fresh value a SEL_MID must deliver.
        for cmd, data in ((CMD_LDA, 100), (CMD_LDB, 100)):
            await command(dut, cmd, data=data)
            golden = apply_command(golden, cmd, data)
        await command(dut, CMD_MAC)
        golden = apply_command(golden, CMD_MAC, 0)
        await command(dut, CMD_SEL_LO)
        golden = apply_command(golden, CMD_SEL_LO, 0)
        await ClockCycles(dut.clk, 2)
        assert int(dut.uo_out.value) == 0x10, "setup failed, low byte not shown"

        # SEL_MID with the rise forced onto one side of a sampling edge.
        dut.ui_in.value = 0
        dut.uio_in.value = CMD_SEL_MID
        await ClockCycles(dut.clk, 2)
        await RisingEdge(dut.clk)
        if slip == 0:
            await timer_ns(CLK_PERIOD_NS - 0.1)
        else:
            await timer_ns(CLK_PERIOD_NS + 0.1)
        dut.uio_in.value = STROBE | CMD_SEL_MID

        # The old v0.4 floor, exactly 4 clocks after the rise, then one
        # clock later, the ruled v0.5 floor, for the record.
        await timer_ns(4 * CLK_PERIOD_NS)
        at_floor = int(dut.uo_out.value)
        await timer_ns(CLK_PERIOD_NS)
        at_floor_plus_one = int(dut.uo_out.value)
        results[name] = (at_floor, at_floor_plus_one)
        dut._log.info(
            "SEL_BOUNDARY %s: floor sample %#04x, floor plus one %#04x, want 0x27",
            name, at_floor, at_floor_plus_one,
        )

        # Finish the pulse legally and settle.
        dut.uio_in.value = CMD_SEL_MID
        await ClockCycles(dut.clk, 3)
        dut.uio_in.value = 0
        await ClockCycles(dut.clk, 2)

    stale = {k: v for k, v in results.items() if v[0] != 0x27}
    assert not stale, (
        f"stale read at the old 4 clock floor: {stale}, "
        "the v0.4 floor licensed sampling at the output register launch instant, "
        "corrected to 5 clocks in spec v0.5"
    )
