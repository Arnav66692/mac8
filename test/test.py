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
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer

from golden import Golden, apply_command
from test_top import (
    CLK_PERIOD_NS,
    CMD_LDA,
    CMD_LDB,
    CMD_MAC,
    CMD_SEL_HI,
    CMD_SEL_LO,
    CMD_SEL_MID,
    STROBE,
    check_pins,
    command,
    pin_fields,
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


# Reviewer directed cases, F1.5 item 2. These are the classes synthesis can
# reintroduce, so they run on the hardened netlist, not just RTL. Pin only.
# Both use off grid strobe timing. A phantom accept or a doubled MAC is made
# visible through the accumulator readback, MAC is the only non idempotent
# command so it is the probe.


@cocotb.test()
async def test_reset_release_strobe_high_gl(dut):
    """Strobe held high across reset release fires no command. Checked at
    release plus one clock and plus two, both off grid. Clean reset state on
    the pins, and zero accepts proven, a phantom LDA of 0x7F would corrupt A
    and a later 0 times followup would not, so a probe MAC exposes it."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    dut.ena.value = 1

    for hold_clocks, phase_ns in ((1, 3.3), (2, 7.1)):
        # Strobe high, cmd LDA, data 0x7F, held across reset. Off grid release.
        dut.ui_in.value = 0x7F
        dut.uio_in.value = STROBE | CMD_LDA
        dut.rst_n.value = 0
        await ClockCycles(dut.clk, 3)
        await Timer(phase_ns, "ns")
        dut.rst_n.value = 1
        await ClockCycles(dut.clk, hold_clocks)

        # Clean reset state on the pins.
        await FallingEdge(dut.clk)
        uo, busy, ovf, low_nibble, reserved = pin_fields(dut)
        assert uo == 0, f"reset strobe high hold {hold_clocks}. uo_out {uo:#04x}"
        assert busy == 0, f"reset strobe high hold {hold_clocks}. busy high"
        assert ovf == 0, f"reset strobe high hold {hold_clocks}. ovf high"
        assert int(dut.uio_oe.value) == 0xF0, "uio_oe wrong after reset"

        # Zero accept probe. Drop the strobe so the arm can set, then a legal
        # LDB 1, MAC, SEL_LO. If a phantom LDA loaded A to 0x7F, acc reads 127.
        # If clean, A stayed 0 and acc reads 0.
        golden = Golden()
        await command(dut, CMD_LDB, data=1)
        golden = apply_command(golden, CMD_LDB, 1)
        await command(dut, CMD_MAC)
        golden = apply_command(golden, CMD_MAC, 0)
        await command(dut, CMD_SEL_LO)
        golden = apply_command(golden, CMD_SEL_LO, 0)
        await check_pins(dut, golden, f"zero accept probe, hold {hold_clocks}")
        assert golden.acc == 0, "golden self check, clean case is acc 0"


@cocotb.test()
async def test_lockout_boundary_gl(dut):
    """The lockout window boundary, through the pins, off grid. A second rise
    4 clocks after the first, inside the window, is ignored, one MAC lands. A
    second rise 5 clocks after, the legal minimum, is accepted, two MACs land.
    Distinguished by the accumulator, 6 times 7 is 42 for one, 84 for two."""
    for rise_to_rise, macs in ((4, 1), (5, 2)):
        await start_and_reset(dut)
        golden = Golden()
        await command(dut, CMD_LDA, data=6)
        golden = apply_command(golden, CMD_LDA, 6)
        await command(dut, CMD_LDB, data=7)
        golden = apply_command(golden, CMD_LDB, 7)

        # Two MAC rises spaced rise_to_rise clocks, high 3 then low the rest.
        low = rise_to_rise - 3
        dut.ui_in.value = 0
        dut.uio_in.value = CMD_MAC
        await ClockCycles(dut.clk, 1)
        await Timer(2.5, "ns")  # off grid, both rises shift off the clock grid
        dut.uio_in.value = STROBE | CMD_MAC
        await ClockCycles(dut.clk, 3)
        dut.uio_in.value = CMD_MAC
        await ClockCycles(dut.clk, low)
        dut.uio_in.value = STROBE | CMD_MAC
        await ClockCycles(dut.clk, 3)
        dut.uio_in.value = CMD_MAC
        await ClockCycles(dut.clk, 4)

        for _ in range(macs):
            golden = apply_command(golden, CMD_MAC, 0)
        await command(dut, CMD_SEL_LO)
        golden = apply_command(golden, CMD_SEL_LO, 0)
        await check_pins(dut, golden, f"lockout rise to rise {rise_to_rise}")
        assert golden.acc == (42 if macs == 1 else 84), "golden self check"


@cocotb.test()
async def test_data_hold_window(dut):
    """Pins the data setup and hold interface rule, spec v0.3. Data must be
    stable while the strobe is high and for 2 clocks after it falls. Load A
    with 0x2A honoring that window, flip the bus to 0xFF right after, then MAC
    by 1 and read acc. A must read 0x2A, so the DUT captured the windowed data
    and a change past the hold boundary does not corrupt it. Off grid."""
    await start_and_reset(dut)
    golden = Golden()
    data = 0x2A

    # LDA with strict interface timing, driven raw on the pins.
    dut.ui_in.value = data
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 1)  # data setup before the strobe rise
    await Timer(2.5, "ns")         # off grid
    dut.uio_in.value = STROBE | CMD_LDA
    await ClockCycles(dut.clk, 3)  # strobe high
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 2)  # hold data 2 clocks after the fall
    dut.ui_in.value = 0xFF         # change the bus past the hold window
    await ClockCycles(dut.clk, 2)
    golden = apply_command(golden, CMD_LDA, data)

    # Read A back, B is 1 so acc equals A.
    await command(dut, CMD_LDB, data=1)
    golden = apply_command(golden, CMD_LDB, 1)
    await command(dut, CMD_MAC)
    golden = apply_command(golden, CMD_MAC, 0)
    await command(dut, CMD_SEL_LO)
    golden = apply_command(golden, CMD_SEL_LO, 0)
    await check_pins(dut, golden, "data hold window")
    assert golden.acc == data, "A did not capture the windowed data"
