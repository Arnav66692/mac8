# measure_delay.py
# Not part of the CI suite. Measures the delay from the launching clock
# edge to the first uo_out transition for one accumulator byte change,
# pin only. Run it against the functional gate level sim and against the
# SDF annotated sim at the same clock period and compare, the numbers are
# recorded in docs/GL_TIMING.md. A nonzero difference is the evidence the
# annotation actually moves simulated time, the round three run had none.
#
#   functional  make GATES=yes MAC8_CLK_PERIOD_NS=20 COCOTB_TEST_MODULES=measure_delay
#   annotated   make -f Makefile.sdf COCOTB_TEST_MODULES=measure_delay

import cocotb
from cocotb.triggers import ClockCycles, Edge, FallingEdge, RisingEdge
from cocotb.utils import get_sim_time

from test_top import CMD_CLR, CMD_LDA, CMD_LDB, CMD_MAC, command, start_and_reset


@cocotb.test()
async def measure_uo_out_delay(dut):
    """Clock edge to uo_out transition, one CLR driven byte change."""
    await start_and_reset(dut)

    # acc to 42, uo_out settles at 0x2A on the reset default low byte select.
    await command(dut, CMD_LDA, data=6)
    await command(dut, CMD_LDB, data=7)
    await command(dut, CMD_MAC)
    await ClockCycles(dut.clk, 4)
    await FallingEdge(dut.clk)
    assert int(dut.uo_out.value) == 0x2A, "setup failed, uo_out not 0x2A"

    # Track the most recent rising clock edge time in the background.
    last_edge = {"ps": None}

    async def posedge_tracker():
        while True:
            await RisingEdge(dut.clk)
            last_edge["ps"] = get_sim_time("ps")

    tracker = cocotb.start_soon(posedge_tracker())

    # CLR drives uo_out from 0x2A to 0x00. The first bit transition after
    # the launching edge is the measured delay.
    cocotb.start_soon(command(dut, CMD_CLR))
    await Edge(dut.uo_out)
    t_change = get_sim_time("ps")
    tracker.cancel()

    assert last_edge["ps"] is not None, "no clock edge observed before the change"
    delay_ps = t_change - last_edge["ps"]
    dut._log.info(
        "MEASURE_DELAY: uo_out first transition %d ps after the launching edge",
        delay_ps,
    )
    assert delay_ps >= 0, "transition before its launching edge"
