# test.py
# Tiny Tapeout CI suite for tt_um_arnav_mac8. PIN ONLY by construction.
# Every test here drives and observes nothing but the external ports, so
# the same suite runs on the RTL and on the hardened gate level netlist,
# where internal hierarchy no longer exists.
#
# One home per test body. The five ported tests import their bodies from
# tb/test_top.py, which also wraps them for the local RTL suite with the
# white box monitors added there. Nothing is duplicated and nothing is
# weakened, checks that need internal signals live in tb/ only.

import cocotb
from cocotb.triggers import ClockCycles

from golden import Golden, apply_command
from test_top import (
    CMD_LDA,
    CMD_LDB,
    CMD_MAC,
    CMD_SEL_HI,
    CMD_SEL_LO,
    CMD_SEL_MID,
    STROBE,
    check_pins,
    command,
    run_dot_product_usage,
    run_every_command_end_to_end,
    run_minimum_strobe_timing,
    run_random_protocol_500,
    run_reset_pin_state,
    start_and_reset,
)


@cocotb.test()
async def test_reset_pin_state(dut):
    """Reset pin state per the spec, pins only."""
    await run_reset_pin_state(dut)


@cocotb.test()
async def test_every_command_end_to_end(dut):
    """Every command code through the pins, NOP included."""
    await run_every_command_end_to_end(dut)


@cocotb.test()
async def test_dot_product_usage(dut):
    """The spec usage sequence plus a saturating variant, ovf pin checked."""
    await run_dot_product_usage(dut)


@cocotb.test()
async def test_minimum_strobe_timing(dut):
    """50 commands at the minimum legal strobe timing."""
    await run_minimum_strobe_timing(dut)


@cocotb.test()
async def test_random_protocol_500(dut):
    """500 random commands with random legal timing against the golden model."""
    await run_random_protocol_500(dut)


@cocotb.test()
async def test_ringing_edge_one_mac_pins(dut):
    """A ringing strobe edge fires exactly one MAC, proven through the pins.

    Preload 6 and 7, ring the strobe with cmd held at MAC, high 2, low 2,
    high 3. Without the lockout two MACs land and acc reads 84. With it,
    exactly one lands and every readback byte matches acc equal 42. This is
    the gate level safe version of the white box lockout test in tb/."""
    await start_and_reset(dut)
    golden = Golden()

    for cmd, data in ((CMD_LDA, 6), (CMD_LDB, 7)):
        await command(dut, cmd, data=data)
        golden = apply_command(golden, cmd, data)

    # The ring, driven raw on the pins, cmd held at MAC throughout.
    dut.ui_in.value = 0
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = STROBE | CMD_MAC
    await ClockCycles(dut.clk, 2)
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 2)
    dut.uio_in.value = STROBE | CMD_MAC
    await ClockCycles(dut.clk, 3)
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 4)

    golden = apply_command(golden, CMD_MAC, 0)
    await check_pins(dut, golden, "one MAC from a ringing edge, pins only")

    # Full readback. All three bytes must match acc equal 42, not 84.
    for cmd, name in ((CMD_SEL_LO, "lo"), (CMD_SEL_MID, "mid"), (CMD_SEL_HI, "hi")):
        await command(dut, cmd)
        golden = apply_command(golden, cmd, 0)
        await check_pins(dut, golden, f"ringing readback {name}")

    # A clean command afterward still works.
    await command(dut, CMD_LDA, data=2)
    golden = apply_command(golden, CMD_LDA, 2)
    await check_pins(dut, golden, "clean command after the ring")
