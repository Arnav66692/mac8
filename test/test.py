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
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer

from golden import INT24_MAX, INT24_MIN, Golden, apply_command
from test_top import (
    CLK_PERIOD_NS,
    CMD_CLR,
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
    reset_only,
    run_dot_product_usage,
    run_every_command_end_to_end,
    run_minimum_strobe_timing,
    run_random_protocol_500,
    run_reset_pin_state,
    start_and_reset,
    start_clock,
    timer_ns,
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

    Preload 6 and 7, ring the strobe with cmd held at MAC, high 2, low 1,
    high 3, a bounce with rises 3 clocks apart. Without the lockout two MACs
    land and acc reads 84. With it, exactly one lands and every readback byte
    matches acc equal 42. This is the gate level safe version of the white
    box lockout test in tb/.

    The bounce tightened from low 2 to low 1 in round two. The lockout is 3
    clocks now, so a bounce with rises 4 clocks apart is no longer blocked.
    At 50 MHz that is an 80 ns oscillation, not signal integrity ringing, and
    at the pins it is indistinguishable from two intended strobes. Blocking
    it is what ate a legal command at the worst async alignment."""
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
    await ClockCycles(dut.clk, 1)
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
    start_clock(dut)
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

        # Clean reset state on the pins, every output field including the
        # reserved bits and the low nibble, audit gap closed.
        await FallingEdge(dut.clk)
        uo, busy, ovf, low_nibble, reserved = pin_fields(dut)
        assert uo == 0, f"reset strobe high hold {hold_clocks}. uo_out {uo:#04x}"
        assert busy == 0, f"reset strobe high hold {hold_clocks}. busy high"
        assert ovf == 0, f"reset strobe high hold {hold_clocks}. ovf high"
        assert low_nibble == 0, (
            f"reset strobe high hold {hold_clocks}. uio_out low nibble {low_nibble:#03x}"
        )
        assert reserved == 0, (
            f"reset strobe high hold {hold_clocks}. reserved bits {reserved}"
        )
        assert int(dut.uio_oe.value) == 0xF0, "uio_oe wrong after reset"

        # Reset rule v0.4. The pad release crosses the two flop reset
        # synchronizer, so the arm settles on the fifth post release clock.
        # Drop the strobe and wait that out before probing, otherwise the
        # probe commands are dropped and the probe reads vacuously.
        dut.uio_in.value = 0
        await ClockCycles(dut.clk, 5)

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
    """The lockout window after the round two width fix, 3 clocks, through
    the pins, off grid. Three cases pin the exact window edges. A bounce with
    rises 3 clocks apart, the ring case, lands its second accept at offset 3,
    inside the window, one MAC. Rises 4 clocks apart land the second accept at
    offset 4, outside the window, two MACs, this row kills a mutation that
    reverts the window to 4 clocks. Rises 5 clocks apart, the legal minimum
    spacing, two MACs, the spacing case.

    The bug the width fix closes cannot appear in this test. The dropped
    command needs accepts from two legal rises to land 4 clocks apart, first
    edge resolving slow at plus 3, second fast at plus 2. Deterministic
    simulation collapses the 2 to 3 latency range to a point, in phase edges
    resolve identically and legal accepts land 5 apart. So this test pins the
    ring case and the spacing case, and the dropped command case is closed by
    the width proof in mac8_sync.sv, not by simulation. The offset 4 row here
    uses out of contract spacing as an RTL property probe, driver facing
    behavior at that spacing is unspecified.

    Distinguished by the accumulator, 6 times 7 is 42 for one MAC, 84 for
    two."""
    await start_and_reset(dut)
    for high, low_clocks, macs, tag in (
        (2, 1, 1, "ring, second accept offset 3, blocked"),
        (3, 1, 2, "window edge, second accept offset 4, passes"),
        (3, 2, 2, "legal minimum, rise to rise 5"),
    ):
        await reset_only(dut)
        golden = Golden()
        await command(dut, CMD_LDA, data=6)
        golden = apply_command(golden, CMD_LDA, 6)
        await command(dut, CMD_LDB, data=7)
        golden = apply_command(golden, CMD_LDB, 7)

        # Two MAC rises, high then low then high 3, rise to rise high plus low.
        dut.ui_in.value = 0
        dut.uio_in.value = CMD_MAC
        await ClockCycles(dut.clk, 1)
        await Timer(2.5, "ns")  # off grid, both rises shift off the clock grid
        dut.uio_in.value = STROBE | CMD_MAC
        await ClockCycles(dut.clk, high)
        dut.uio_in.value = CMD_MAC
        await ClockCycles(dut.clk, low_clocks)
        dut.uio_in.value = STROBE | CMD_MAC
        await ClockCycles(dut.clk, 3)
        dut.uio_in.value = CMD_MAC
        await ClockCycles(dut.clk, 4)

        for _ in range(macs):
            golden = apply_command(golden, CMD_MAC, 0)
        await command(dut, CMD_SEL_LO)
        golden = apply_command(golden, CMD_SEL_LO, 0)
        await check_pins(dut, golden, f"lockout {tag}")
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


# Submission readiness audit additions, 2026-08. GL safe, pin only. These
# close the observation gaps the audit named. Busy was asserted between
# commands but never observed high during one. The rails were reached but
# never read back exactly at both ends. The mid strobe reset replay ran
# white box only. The hold window exercised ui_in but not the command bits.


@cocotb.test()
async def test_busy_pin_pulse_gl(dut):
    """Busy observed at the pin, high for exactly one cycle during a MAC,
    low after it, and never high across a non MAC command. Pin only, the
    white box busy test in tb/ reads u_sync.accept and cannot run here.
    Sampling on falling edges across the command window catches the one
    busy cycle at either synchronizer latency. Killed by a busy tied low
    mutation, which every other pin test survives."""
    await start_and_reset(dut)
    golden = Golden()
    await command(dut, CMD_LDA, data=7)
    golden = apply_command(golden, CMD_LDA, 7)
    await command(dut, CMD_LDB, data=9)
    golden = apply_command(golden, CMD_LDB, 9)

    # The command helper drives legal timing in the background while the
    # foreground samples busy at the pin on every falling edge.
    task = cocotb.start_soon(command(dut, CMD_MAC, high=3, low=3, setup=1))
    busy_cycles = 0
    for _ in range(10):
        await FallingEdge(dut.clk)
        busy_cycles += (int(dut.uio_out.value) >> 4) & 1
    await task
    golden = apply_command(golden, CMD_MAC, 0)

    assert busy_cycles == 1, f"busy high {busy_cycles} cycles across a MAC, want 1"
    await check_pins(dut, golden, "busy low again after the MAC")

    # A non MAC command never raises busy, sampled across its whole window.
    task = cocotb.start_soon(command(dut, CMD_SEL_MID, high=3, low=3, setup=1))
    busy_seen = 0
    for _ in range(10):
        await FallingEdge(dut.clk)
        busy_seen += (int(dut.uio_out.value) >> 4) & 1
    await task
    golden = apply_command(golden, CMD_SEL_MID, 0)
    assert busy_seen == 0, "busy rose on a non MAC command"
    await check_pins(dut, golden, "after the non MAC busy watch")


async def read_acc24(dut, golden):
    """Read the full 24 bit accumulator through the three SEL commands.
    Returns the reconstructed value as the golden model tracks it."""
    readback = {}
    for cmd, name in ((CMD_SEL_LO, "lo"), (CMD_SEL_MID, "mid"), (CMD_SEL_HI, "hi")):
        await command(dut, cmd)
        golden_next = apply_command(golden, cmd, 0)
        await check_pins(dut, golden_next, f"rail readback {name}")
        readback[name] = int(dut.uo_out.value)
        golden = golden_next
    value = readback["lo"] | (readback["mid"] << 8) | (readback["hi"] << 16)
    return value, golden


@cocotb.test()
async def test_rail_landings_gl(dut):
    """Exact rail landings observed through SEL readback at both rails.

    Each rail is reached twice. First an exact landing, the accumulator
    arithmetic sums to the rail value precisely, no saturation event, the
    ovf pin must stay low and all three bytes must read the rail pattern.
    Then one more MAC crosses the rail, saturation clamps, ovf goes high,
    and the bytes must still read the rail pattern. The exact landing rows
    kill a mutation that writes the rail compare inclusive, greater or
    equal instead of greater, which flags saturation on a legal sum that
    merely equals the rail."""
    await start_and_reset(dut)
    golden = Golden()

    async def mac_times(a, b, n, golden):
        await command(dut, CMD_LDA, data=a & 0xFF)
        golden = apply_command(golden, CMD_LDA, a & 0xFF)
        await command(dut, CMD_LDB, data=b & 0xFF)
        golden = apply_command(golden, CMD_LDB, b & 0xFF)
        for _ in range(n):
            await command(dut, CMD_MAC)
            golden = apply_command(golden, CMD_MAC, 0)
        return golden

    # Positive rail, exact. 520 times 127x127 plus 100x14 plus 127x1
    # equals 8388607 on the nose.
    golden = await mac_times(127, 127, 520, golden)
    golden = await mac_times(100, 14, 1, golden)
    golden = await mac_times(127, 1, 1, golden)
    value, golden = await read_acc24(dut, golden)
    assert golden.acc == INT24_MAX and not golden.ovf, "golden self check, exact +rail"
    assert value == 0x7FFFFF, f"exact +rail read {value:#08x}, want 0x7fffff"
    _, _, ovf, _, _ = pin_fields(dut)
    assert ovf == 0, "ovf high on an exact +rail landing, no saturation happened"

    # Cross it. One more positive product saturates and sets ovf.
    golden = await mac_times(1, 1, 1, golden)
    value, golden = await read_acc24(dut, golden)
    assert golden.acc == INT24_MAX and golden.ovf, "golden self check, +rail cross"
    assert value == 0x7FFFFF, f"+rail after cross read {value:#08x}"
    _, _, ovf, _, _ = pin_fields(dut)
    assert ovf == 1, "ovf low after crossing the +rail"

    # Negative rail, exact. CLR, then 516 times -128x127 plus -128x4
    # equals -8388608 on the nose.
    await command(dut, CMD_CLR)
    golden = apply_command(golden, CMD_CLR, 0)
    golden = await mac_times(-128, 127, 516, golden)
    golden = await mac_times(-128, 4, 1, golden)
    value, golden = await read_acc24(dut, golden)
    assert golden.acc == INT24_MIN and not golden.ovf, "golden self check, exact -rail"
    assert value == 0x800000, f"exact -rail read {value:#08x}, want 0x800000"
    _, _, ovf, _, _ = pin_fields(dut)
    assert ovf == 0, "ovf high on an exact -rail landing, no saturation happened"

    # Cross it. One more negative product saturates and sets ovf.
    golden = await mac_times(-128, 1, 1, golden)
    value, golden = await read_acc24(dut, golden)
    assert golden.acc == INT24_MIN and golden.ovf, "golden self check, -rail cross"
    assert value == 0x800000, f"-rail after cross read {value:#08x}"
    _, _, ovf, _, _ = pin_fields(dut)
    assert ovf == 1, "ovf low after crossing the -rail"


@cocotb.test()
async def test_reset_replay_gl(dut):
    """Mid strobe reset does not replay the in flight command, on the gate
    netlist. The white box version counts u_sync.accept and cannot run
    here, so the replay is made visible through the accumulator. A LDA of
    0x5A is in flight when reset lands. If it replays after release, A
    holds 0x5A and a probe MAC by 1 reads 0x5A. Clean, A holds 0 and the
    probe reads 0."""
    await start_and_reset(dut)

    # A legal LDA raised and held, reset pulsed mid strobe, strobe stays
    # high across the pulse, same shape as the white box original.
    dut.ui_in.value = 0x5A
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 1)
    await Timer(2500, "ps")  # off grid
    dut.uio_in.value = STROBE | CMD_LDA
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    # Hold the strobe high across release, wait out any replay window,
    # then check clean reset state on every pin field.
    await ClockCycles(dut.clk, 8)
    await FallingEdge(dut.clk)
    uo, busy, ovf, low_nibble, reserved = pin_fields(dut)
    assert uo == 0, f"reset replay. uo_out {uo:#04x} after mid strobe reset"
    assert busy == 0, "reset replay. busy high after mid strobe reset"
    assert ovf == 0, "reset replay. ovf high after mid strobe reset"
    assert low_nibble == 0, "reset replay. uio_out low nibble nonzero"
    assert reserved == 0, "reset replay. reserved bits nonzero"

    # Arm per the reset rule, then probe. LDB 1, MAC, SEL_LO. A replayed
    # LDA leaves acc at 0x5A, clean leaves 0.
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    golden = Golden()
    await command(dut, CMD_LDB, data=1)
    golden = apply_command(golden, CMD_LDB, 1)
    await command(dut, CMD_MAC)
    golden = apply_command(golden, CMD_MAC, 0)
    await command(dut, CMD_SEL_LO)
    golden = apply_command(golden, CMD_SEL_LO, 0)
    await check_pins(dut, golden, "reset replay probe")
    assert golden.acc == 0, "golden self check, clean case is acc 0"


@cocotb.test()
async def test_cmd_hold_window(dut):
    """The data hold requirement exercised on the command bits, spec v0.3.
    uio[2:0] must stay stable while the strobe is high and for 2 clocks
    after the fall. Run a LDA honoring that window, then flip the command
    bits to CLR exactly at the hold boundary with the strobe low. The LDA
    must have latched, and no CLR may fire off the dead command bus. The
    accumulator is preloaded nonzero so a phantom CLR is visible. Off
    grid."""
    await start_and_reset(dut)
    golden = Golden()

    # Preload acc to a nonzero value a phantom CLR would wipe.
    await command(dut, CMD_LDA, data=3)
    golden = apply_command(golden, CMD_LDA, 3)
    await command(dut, CMD_LDB, data=11)
    golden = apply_command(golden, CMD_LDB, 11)
    await command(dut, CMD_MAC)
    golden = apply_command(golden, CMD_MAC, 0)
    await check_pins(dut, golden, "cmd hold preload")

    # LDA 0x2A with strict interface timing, driven raw on the pins.
    data = 0x2A
    dut.ui_in.value = data
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 1)
    await Timer(2500, "ps")
    dut.uio_in.value = STROBE | CMD_LDA
    await ClockCycles(dut.clk, 3)   # strobe high
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 2)   # hold cmd 2 clocks after the fall
    dut.uio_in.value = CMD_CLR      # flip the command bus past the boundary
    await ClockCycles(dut.clk, 3)
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 2)
    golden = apply_command(golden, CMD_LDA, data)

    # If the CLR fired, acc is 0 and ovf state wiped. If the LDA missed,
    # A is stale. Probe with MAC by B=1... B is 11, use it directly.
    await command(dut, CMD_MAC)
    golden = apply_command(golden, CMD_MAC, 0)
    await command(dut, CMD_SEL_LO)
    golden = apply_command(golden, CMD_SEL_LO, 0)
    await check_pins(dut, golden, "cmd hold window probe")
    assert golden.acc == 3 * 11 + data * 11, "golden self check"


@cocotb.test()
async def test_sel_read_floor(dut):
    """Pins the v0.5 SEL read rule, sample uo_out no earlier than 5 clocks
    after the strobe rise. The rise is forced onto each side of a sampling
    edge, the latency grid technique, so both synchronizer resolutions are
    exercised, and the byte sampled at exactly rise plus 5 clocks must be
    fresh in both. The stale read at the old 4 clock floor is demonstrated
    by test/probe_sel_boundary.py, kept outside this suite because its
    clk to Q race is corner dependent, the spec v0.5 changelog cites it as
    the contract evidence."""
    await start_and_reset(dut)

    for slip, name in ((0, "fast, resolves in 2"), (1, "slow, resolves in 3")):
        await reset_only(dut)
        golden = Golden()

        # acc to 10000, 0x002710. Low byte 0x10 shows on the reset default
        # select, mid byte 0x27 is the fresh value SEL_MID must deliver.
        for cmd, val in ((CMD_LDA, 100), (CMD_LDB, 100)):
            await command(dut, cmd, data=val)
            golden = apply_command(golden, cmd, val)
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

        # The earliest legal sample under the v0.5 rule.
        await timer_ns(5 * CLK_PERIOD_NS)
        sampled = int(dut.uo_out.value)
        assert sampled == 0x27, (
            f"SEL read at the 5 clock floor, {name}, read {sampled:#04x}, "
            "want the fresh mid byte 0x27"
        )

        # Finish the pulse legally and settle.
        dut.uio_in.value = CMD_SEL_MID
        await ClockCycles(dut.clk, 3)
        dut.uio_in.value = 0
        await ClockCycles(dut.clk, 2)
