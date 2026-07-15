# test_top.py
# Protocol level tests for tt_um_arnav_mac8, the module formerly named
# mac8_top. External ports only for stimulus.
# The driver obeys the SPEC.md rules. Data and command first, then the
# strobe rise. Strobe high at least 3 core clocks, low at least 2 before
# the next rise. Data stable while the strobe is high plus 2 clocks after
# the fall. One helper performs a single command, every test builds on it.
# Checks sample on falling edges, so values are settled.
#
# Gate level prep, F7. Some helpers and tests read internal hierarchy for
# observation only, never for stimulus. These cannot run against a gate
# level netlist, whose internal names are gone. Each is tagged WHITE BOX
# below. The gate level subset split happens in the TT integration task.
# Reads u_sync.accept, count fired commands. accept_busy_monitor,
# count_accepts, count_accepts_span, measure_accept_offset, measure_one_fire,
# test_long_strobe_single_fire, test_busy_pulse_on_mac, test_ringing_edge_lockout.
# Reads u_dp.out_sel_q, the byte select. assert_reset_state.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer

from golden import INT24_MAX, Golden, apply_command

CLK_PERIOD_NS = 10

CMD_NOP = 0
CMD_CLR = 1
CMD_LDA = 2
CMD_LDB = 3
CMD_MAC = 4
CMD_SEL_LO = 5
CMD_SEL_MID = 6
CMD_SEL_HI = 7

STROBE = 0x08
UIO_OE_EXPECTED = 0xF0

RANDOM_CMDS = 500
RANDOM_SEED = 20260714

# Phase randomization. Every strobe rise gets a sub cycle offset so it lands
# off the clock grid, exercising the synchronizer with truly asynchronous
# edges instead of clock aligned ones. Fixed seed for reproducibility, logged
# once per run. The offset is sub cycle, so edge count based assertions hold.
PHASE_SEED = 20260713
_phase_rng = random.Random(PHASE_SEED)
_phase_logged = False


async def start_and_reset(dut):
    """Start the clock and apply reset per the v0.4 reset rule.

    rst_n crosses a two flop synchronizer inside the design, round two item
    6, so assertion needs 3 clocks to act, 2 to cross plus 1 to clear, and
    the arm settles on the fifth clock after pad release. Hold reset low 4
    clocks, then hold strobe low 5 clocks after release before any rise."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def command(dut, cmd, data=0, high=3, low=2, setup=1):
    """One command per the spec driver rules.

    Data and command are written first, the strobe rises after them.
    With setup 0 the rise lands in the same window as the data write,
    which is the minimum legal profile. The command executes before this
    helper returns, so pins are stable for checks right after it.

    The strobe rise gets a sub cycle phase offset so it lands off the clock
    grid. Sub cycle keeps the edge count to accept unchanged, so exact cycle
    assertions still hold, but the synchronizer sees a truly async edge."""
    global _phase_logged
    if not _phase_logged:
        dut._log.info(f"phase randomization on, seed {PHASE_SEED}")
        _phase_logged = True
    dut.ui_in.value = data & 0xFF
    dut.uio_in.value = cmd & 0x7
    if setup:
        await ClockCycles(dut.clk, setup)
    # Round to 0.1 ns so the offset is an exact number of simulator steps,
    # still off the 10 ns clock grid.
    await Timer(round(_phase_rng.uniform(0.5, CLK_PERIOD_NS - 0.5), 1), "ns")
    dut.uio_in.value = STROBE | (cmd & 0x7)
    await ClockCycles(dut.clk, high)
    dut.uio_in.value = cmd & 0x7
    await ClockCycles(dut.clk, low)


def pin_fields(dut):
    """Decode the output pins. Returns uo_out, busy, ovf, low nibble, reserved."""
    uio = int(dut.uio_out.value)
    return (
        int(dut.uo_out.value),
        (uio >> 4) & 1,
        (uio >> 5) & 1,
        uio & 0x0F,
        (uio >> 6) & 0x3,
    )


async def check_pins(dut, golden, tag):
    """Settled pin check against the golden model, between commands."""
    await FallingEdge(dut.clk)
    uo, busy, ovf, low_nibble, reserved = pin_fields(dut)
    want = golden.acc_byte()
    assert uo == want, f"{tag}. uo_out {uo:#04x}, want {want:#04x}"
    assert ovf == int(golden.ovf), f"{tag}. ovf pin {ovf}, want {int(golden.ovf)}"
    assert busy == 0, f"{tag}. busy pin high between commands"
    assert low_nibble == 0, f"{tag}. uio_out low nibble {low_nibble:#03x}, want 0"
    assert reserved == 0, f"{tag}. reserved bits {reserved}, want 0"
    assert int(dut.uio_oe.value) == UIO_OE_EXPECTED, f"{tag}. uio_oe wrong"


async def accept_busy_monitor(dut):
    """Asserts busy is never high in a cycle where an accept fires.

    Documents that the busy ignore path is unreachable at v0.1 timing.
    WHITE BOX, reads u_sync.accept, observation only, not for gate level."""
    while True:
        await FallingEdge(dut.clk)
        try:
            fired = int(dut.u_sync.accept.value)
        except ValueError:
            # X before reset resolves, outside this monitor's claim.
            continue
        if fired == 1:
            busy = (int(dut.uio_out.value) >> 4) & 1
            assert busy == 0, "accept fired while busy is high"


# Test partition, F6. The run_* coroutines below are PIN ONLY, they drive
# and observe nothing but the external ports, so they run unchanged on the
# gate level netlist. test/test.py imports and wraps them for the Tiny
# Tapeout CI, at RTL and at gate level. The @cocotb.test wrappers here add
# the white box monitors where they were, RTL only. Tests further down that
# read internal hierarchy are WHITE BOX and stay in this suite only.


async def run_reset_pin_state(dut):
    """PIN ONLY. Reset pin state. uo_out 0, busy 0, ovf 0, uio_oe 11110000."""
    await start_and_reset(dut)
    await FallingEdge(dut.clk)
    uo, busy, ovf, low_nibble, reserved = pin_fields(dut)
    assert uo == 0, "uo_out not 0 after reset"
    assert busy == 0, "busy not 0 after reset"
    assert ovf == 0, "ovf not 0 after reset"
    assert low_nibble == 0, "uio_out low nibble not 0 after reset"
    assert reserved == 0, "reserved bits not 0 after reset"
    assert int(dut.uio_oe.value) == UIO_OE_EXPECTED, "uio_oe not 11110000"


@cocotb.test()
async def test_reset_pin_state(dut):
    """Reset pin state, RTL wrapper for the pin only body."""
    await run_reset_pin_state(dut)


async def run_every_command_end_to_end(dut):
    """PIN ONLY. Every command code through the pins. NOP included."""
    await start_and_reset(dut)
    golden = Golden()

    await command(dut, CMD_LDA, data=100)
    golden = apply_command(golden, CMD_LDA, 100)
    await check_pins(dut, golden, "LDA")

    await command(dut, CMD_LDB, data=(-3) & 0xFF)
    golden = apply_command(golden, CMD_LDB, (-3) & 0xFF)
    await check_pins(dut, golden, "LDB")

    await command(dut, CMD_MAC)
    golden = apply_command(golden, CMD_MAC, 0)
    await check_pins(dut, golden, "MAC")
    assert golden.acc == -300, "golden model self check failed"

    for cmd, tag in ((CMD_SEL_MID, "SEL_MID"), (CMD_SEL_HI, "SEL_HI"), (CMD_SEL_LO, "SEL_LO")):
        await command(dut, cmd)
        golden = apply_command(golden, cmd, 0)
        await check_pins(dut, golden, tag)

    await command(dut, CMD_NOP, data=0x5A)
    golden = apply_command(golden, CMD_NOP, 0x5A)
    await check_pins(dut, golden, "NOP")
    assert golden.acc == -300, "golden model self check failed"

    await command(dut, CMD_CLR)
    golden = apply_command(golden, CMD_CLR, 0)
    await check_pins(dut, golden, "CLR")
    assert golden.acc == 0, "golden model self check failed"


@cocotb.test()
async def test_every_command_end_to_end(dut):
    """Every command end to end, RTL wrapper for the pin only body."""
    await run_every_command_end_to_end(dut)


async def dot_product(dut, golden, pairs, tag):
    """The spec usage sequence. CLR, then LDA, LDB, MAC per element."""
    await command(dut, CMD_CLR)
    golden = apply_command(golden, CMD_CLR, 0)
    for x, w in pairs:
        await command(dut, CMD_LDA, data=x & 0xFF)
        golden = apply_command(golden, CMD_LDA, x & 0xFF)
        await command(dut, CMD_LDB, data=w & 0xFF)
        golden = apply_command(golden, CMD_LDB, w & 0xFF)
        await command(dut, CMD_MAC)
        golden = apply_command(golden, CMD_MAC, 0)

    # Readback per the spec usage section. SEL then read uo_out.
    readback = {}
    for cmd, name in ((CMD_SEL_LO, "lo"), (CMD_SEL_MID, "mid"), (CMD_SEL_HI, "hi")):
        await command(dut, cmd)
        golden = apply_command(golden, cmd, 0)
        await check_pins(dut, golden, f"{tag} readback {name}")
        readback[name] = int(dut.uo_out.value)

    recon = readback["lo"] | (readback["mid"] << 8) | (readback["hi"] << 16)
    assert recon == golden.acc & 0xFFFFFF, f"{tag}. reconstructed acc {recon:#08x} wrong"
    return golden


async def run_dot_product_usage(dut):
    """PIN ONLY. Dot product of 24 elements per the spec usage section,
    then a saturating variant with the ovf pin checked."""
    await start_and_reset(dut)
    golden = Golden()
    rng = random.Random(RANDOM_SEED)

    pairs = [(rng.randrange(256), rng.randrange(256)) for _ in range(24)]
    golden = await dot_product(dut, golden, pairs, "dot product")
    _, _, ovf, _, _ = pin_fields(dut)
    assert ovf == 0, "clean dot product raised the ovf pin"

    # Saturating variant. 520 max negative squares pass the positive rail.
    pairs = [((-128) & 0xFF, (-128) & 0xFF)] * 520
    golden = await dot_product(dut, golden, pairs, "saturating dot product")
    assert golden.acc == INT24_MAX, "golden model self check failed"
    assert golden.ovf, "golden model self check failed"
    await FallingEdge(dut.clk)
    _, _, ovf, _, _ = pin_fields(dut)
    assert ovf == 1, "ovf pin low after a saturating dot product"


@cocotb.test()
async def test_dot_product_usage(dut):
    """Dot product usage, RTL wrapper for the pin only body."""
    await run_dot_product_usage(dut)


async def run_minimum_strobe_timing(dut):
    """PIN ONLY. Exactly 3 high and 2 low, 50 commands back to back.

    The data write and the strobe rise share one window, data written
    first, which is the minimum the driver rules allow."""
    await start_and_reset(dut)
    golden = Golden()
    rng = random.Random(RANDOM_SEED + 1)

    for i in range(50):
        cmd = rng.randrange(8)
        data = rng.randrange(256)
        await command(dut, cmd, data=data, high=3, low=2, setup=0)
        golden = apply_command(golden, cmd, data)
        await check_pins(dut, golden, f"minimum timing command {i}, code {cmd}")


@cocotb.test()
async def test_minimum_strobe_timing(dut):
    """Minimum strobe timing, RTL wrapper, adds the white box busy monitor."""
    monitor = cocotb.start_soon(accept_busy_monitor(dut))
    await run_minimum_strobe_timing(dut)
    monitor.cancel()


@cocotb.test()
async def test_long_strobe_single_fire(dut):
    """A strobe held high for 100 clocks fires exactly one command."""
    await start_and_reset(dut)
    golden = Golden()

    await command(dut, CMD_LDA, data=3)
    golden = apply_command(golden, CMD_LDA, 3)
    await command(dut, CMD_LDB, data=5)
    golden = apply_command(golden, CMD_LDB, 5)

    dut.ui_in.value = 0
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = STROBE | CMD_MAC
    accepts = 0
    for _ in range(100):
        await FallingEdge(dut.clk)
        accepts += int(dut.u_sync.accept.value)
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 3)

    golden = apply_command(golden, CMD_MAC, 0)
    assert accepts == 1, f"strobe held 100 clocks fired {accepts} accepts"
    await check_pins(dut, golden, "single MAC from a long strobe")
    assert golden.acc == 15, "golden model self check failed"


async def run_random_protocol_500(dut):
    """PIN ONLY. 500 random commands with random legal timing against the
    golden model, uo_out and the ovf pin checked after every command."""
    await start_and_reset(dut)
    golden = Golden()
    rng = random.Random(RANDOM_SEED + 2)

    for i in range(RANDOM_CMDS):
        cmd = rng.randrange(8)
        data = rng.randrange(256)
        high = rng.randrange(3, 6)
        low = rng.randrange(2, 5)
        setup = rng.randrange(0, 2)
        await command(dut, cmd, data=data, high=high, low=low, setup=setup)
        golden = apply_command(golden, cmd, data)
        await check_pins(dut, golden, f"random command {i}, code {cmd}")

    dut._log.info(f"{RANDOM_CMDS} random commands done. final acc {golden.acc}")


@cocotb.test()
async def test_random_protocol_500(dut):
    """Random protocol run, RTL wrapper, adds the white box busy monitor."""
    monitor = cocotb.start_soon(accept_busy_monitor(dut))
    await run_random_protocol_500(dut)
    monitor.cancel()


@cocotb.test()
async def test_busy_pulse_on_mac(dut):
    """Busy pulses high for exactly one cycle per accepted MAC, the cycle
    after the accept. A non MAC command never raises it. This is the
    positive half of the busy contract, a stuck low busy pin fails here."""
    await start_and_reset(dut)
    golden = Golden()
    await command(dut, CMD_LDA, data=7)
    golden = apply_command(golden, CMD_LDA, 7)
    await command(dut, CMD_LDB, data=9)
    golden = apply_command(golden, CMD_LDB, 9)

    task = cocotb.start_soon(command(dut, CMD_MAC, high=3, low=3, setup=1))
    trace = []
    for _ in range(10):
        await FallingEdge(dut.clk)
        accept_bit = int(dut.u_sync.accept.value)
        busy_bit = (int(dut.uio_out.value) >> 4) & 1
        trace.append((accept_bit, busy_bit))
    await task
    golden = apply_command(golden, CMD_MAC, 0)

    accepts = [i for i, (a, _) in enumerate(trace) if a]
    busys = [i for i, (_, b) in enumerate(trace) if b]
    assert len(accepts) == 1, f"expected one accept, saw cycles {accepts}"
    assert len(busys) == 1, f"expected one busy cycle, saw cycles {busys}"
    assert busys[0] == accepts[0] + 1, (
        f"busy at cycle {busys[0]}, accept at {accepts[0]}, want accept plus 1"
    )
    await check_pins(dut, golden, "after the busy pulse MAC")

    task = cocotb.start_soon(command(dut, CMD_SEL_MID, high=3, low=3, setup=1))
    busy_seen = 0
    for _ in range(10):
        await FallingEdge(dut.clk)
        busy_seen += (int(dut.uio_out.value) >> 4) & 1
    await task
    golden = apply_command(golden, CMD_SEL_MID, 0)
    assert busy_seen == 0, "busy rose on a non MAC command"
    await check_pins(dut, golden, "after the non MAC busy watch")


async def measure_accept_offset(dut, phase_ns):
    """Raise the strobe phase_ns into a cycle, truly asynchronous.

    Returns how many rising edges pass between the first edge that
    samples the strobe high and the accept cycle. The consuming latch is
    one edge after the accept cycle, so an offset of 2 means the command
    fires 2 to 3 core clocks after the external edge for any phase.
    WHITE BOX, reads u_sync.accept, not for gate level."""
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 3)
    await RisingEdge(dut.clk)
    await Timer(phase_ns, "ns")
    dut.uio_in.value = STROBE | CMD_MAC
    edges = 0
    seen = None
    while seen is None and edges < 8:
        await RisingEdge(dut.clk)
        edges += 1
        await FallingEdge(dut.clk)
        if int(dut.u_sync.accept.value) == 1:
            seen = edges
    while edges < 4:
        await RisingEdge(dut.clk)
        edges += 1
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 2)
    return seen


@cocotb.test()
async def test_accept_latency_two_to_three(dut):
    """The command fires 2 to 3 core clocks after the external strobe
    edge, for any edge phase. Pins the synchronizer depth both ways. An
    edge detect off ff1 lands early, a registered accept lands late."""
    await start_and_reset(dut)
    golden = Golden()
    await command(dut, CMD_LDA, data=1)
    golden = apply_command(golden, CMD_LDA, 1)
    await command(dut, CMD_LDB, data=1)
    golden = apply_command(golden, CMD_LDB, 1)

    for phase_ns in (2.5, 5.0, 7.5):
        seen = await measure_accept_offset(dut, phase_ns)
        golden = apply_command(golden, CMD_MAC, 0)
        assert seen == 2, (
            f"phase {phase_ns} ns. accept {seen} cycles after the first "
            f"sampling edge, expected 2"
        )
        await check_pins(dut, golden, f"latency probe at phase {phase_ns} ns")


@cocotb.test()
async def test_busy_never_on_accept(dut):
    """Busy is never high when an accept fires. The ctrl ignore path is
    therefore unreachable at v0.1 timing. This test documents it with a
    MAC heavy stream at the minimum legal spacing."""
    await start_and_reset(dut)
    monitor = cocotb.start_soon(accept_busy_monitor(dut))
    golden = Golden()

    await command(dut, CMD_LDA, data=2, setup=0)
    golden = apply_command(golden, CMD_LDA, 2)
    await command(dut, CMD_LDB, data=3, setup=0)
    golden = apply_command(golden, CMD_LDB, 3)
    for _ in range(40):
        await command(dut, CMD_MAC, high=3, low=2, setup=0)
        golden = apply_command(golden, CMD_MAC, 0)

    await check_pins(dut, golden, "MAC heavy minimum spacing stream")
    assert golden.acc == 240, "golden model self check failed"
    monitor.cancel()


# Reset arming tests, the v0.2 fix. These drive only external pins. They
# read u_sync.accept to count fired commands and u_dp.out_sel_q for the
# byte select, the same white box reads the latency tests already use.


async def count_accepts(dut, cycles):
    """Count accept pulses over a window, sampled on falling edges.
    WHITE BOX, reads u_sync.accept, not for gate level."""
    n = 0
    for _ in range(cycles):
        await FallingEdge(dut.clk)
        n += int(dut.u_sync.accept.value)
    return n


def assert_reset_state(dut, tag):
    """Every reset state value, checked on pins plus the byte select.
    WHITE BOX, reads u_dp.out_sel_q, not for gate level."""
    uo, busy, ovf, low_nibble, reserved = pin_fields(dut)
    assert uo == 0, f"{tag}. uo_out {uo:#04x}, want 0"
    assert busy == 0, f"{tag}. busy pin high"
    assert ovf == 0, f"{tag}. ovf pin high"
    assert low_nibble == 0, f"{tag}. uio_out low nibble {low_nibble:#03x}, want 0"
    assert reserved == 0, f"{tag}. reserved bits {reserved}, want 0"
    assert int(dut.uio_oe.value) == UIO_OE_EXPECTED, f"{tag}. uio_oe wrong"
    assert int(dut.u_dp.out_sel_q.value) == 0, f"{tag}. out_sel not low byte"


async def measure_one_fire(dut, cmd, window=8):
    """Strobe is already low with cmd staged. Raise it, return the offset
    to the first accept and the total accepts over the window.
    WHITE BOX, reads u_sync.accept, not for gate level."""
    dut.uio_in.value = STROBE | (cmd & 0x7)
    first = None
    total = 0
    for i in range(1, window + 1):
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        got = int(dut.u_sync.accept.value)
        total += got
        if got and first is None:
            first = i
    return first, total


@cocotb.test()
async def test_strobe_high_across_reset(dut):
    """Strobe held high across reset release fires no command. Then a
    clean low, high sequence fires exactly one, at normal latency."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    dut.ena.value = 1
    # A nonzero command and data held high with the strobe through reset.
    dut.ui_in.value = 0x5A
    dut.uio_in.value = STROBE | CMD_LDA
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    accepts = await count_accepts(dut, 20)
    assert accepts == 0, f"strobe high across reset fired {accepts} accepts"
    await FallingEdge(dut.clk)
    assert_reset_state(dut, "strobe high across reset")

    # Drop the strobe, wait the legal low time, raise it. One command fires.
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 3)
    first, total = await measure_one_fire(dut, CMD_LDA)
    assert total == 1, f"clean rise after reset fired {total} accepts, want 1"
    assert first in (2, 3), f"accept latency {first} clocks, want 2 to 3"


@cocotb.test()
async def test_reset_replay(dut):
    """A reset pulse during a legal strobe does not replay the in flight
    command. State stays clean reset until a fresh edge arrives."""
    await start_and_reset(dut)

    # A legal command, strobe raised and held high.
    dut.ui_in.value = 0x5A
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = STROBE | CMD_LDA
    await ClockCycles(dut.clk, 4)

    # Pulse reset mid strobe. The strobe stays high across it.
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1

    accepts = await count_accepts(dut, 20)
    assert accepts == 0, f"reset mid strobe replayed, {accepts} accepts"
    await FallingEdge(dut.clk)
    assert_reset_state(dut, "reset replay")

    # A fresh low, high edge fires exactly one command, normal latency.
    dut.uio_in.value = CMD_LDA
    await ClockCycles(dut.clk, 3)
    first, total = await measure_one_fire(dut, CMD_LDA)
    assert total == 1, f"fresh edge after reset fired {total} accepts, want 1"
    assert first in (2, 3), f"accept latency {first} clocks, want 2 to 3"


@cocotb.test()
async def test_in_flight_cancel(dut):
    """A reset right after the external edge leaves clean reset state. With
    the round two reset synchronizer the pad assert lands internally 2
    clocks later, so the command can execute in that crossing window and is
    then wiped by the internal reset. Through the pins the outcome is
    identical, no accept after release, state is clean reset."""
    await start_and_reset(dut)

    # Load real operands so a stray MAC would move acc off 0.
    await command(dut, CMD_LDA, data=5)
    await command(dut, CMD_LDB, data=7)

    # Raise the strobe for a MAC, then reset 1 clock later, before accept.
    dut.ui_in.value = 0
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = STROBE | CMD_MAC
    await ClockCycles(dut.clk, 1)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1

    accepts = await count_accepts(dut, 20)
    assert accepts == 0, f"cancelled MAC executed after reset, {accepts} accepts"
    await FallingEdge(dut.clk)
    assert_reset_state(dut, "in flight cancel")

    # Reset wiped the operands. A fresh MAC now is 0 times 0, acc stays 0.
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 3)
    first, total = await measure_one_fire(dut, CMD_MAC)
    assert total == 1, f"fresh MAC after reset fired {total} accepts, want 1"
    assert first in (2, 3), f"accept latency {first} clocks, want 2 to 3"
    await FallingEdge(dut.clk)
    uo, _, ovf, _, _ = pin_fields(dut)
    assert uo == 0, f"acc not 0 after a post reset MAC, uo_out {uo:#04x}"
    assert ovf == 0, "ovf set after a clean post reset MAC"


# F3 lockout test, through the pins. WHITE BOX, reads u_sync.accept to count
# fires, since no clean pin reports a fire. The stimulus is pins only.


async def count_accepts_span(dut, uio_high, uio_low, edges):
    """Drive uio_high for the span, sample accept on each of edges falling
    edges, return the total accepts seen. Used to count across a ring.
    WHITE BOX, reads u_sync.accept, not for gate level."""
    dut.uio_in.value = uio_high if uio_high is not None else uio_low
    n = 0
    for _ in range(edges):
        await FallingEdge(dut.clk)
        n += int(dut.u_sync.accept.value)
    return n


@cocotb.test()
async def test_ringing_edge_lockout(dut):
    """A ringing strobe, high 2 low 2 high 3, makes two synchronized rising
    edges from one physical strobe. The lockout must let exactly one MAC
    execute. acc changes once, and the next legal command is clean."""
    await start_and_reset(dut)
    golden = Golden()

    # Preload operands so a MAC moves acc off 0 and a double MAC would show.
    await command(dut, CMD_LDA, data=6)
    golden = apply_command(golden, CMD_LDA, 6)
    await command(dut, CMD_LDB, data=7)
    golden = apply_command(golden, CMD_LDB, 7)

    # Ringing strobe, cmd held at MAC. Count accepts across the whole ring.
    dut.ui_in.value = 0
    dut.uio_in.value = CMD_MAC
    await ClockCycles(dut.clk, 1)
    accepts = 0
    accepts += await count_accepts_span(dut, STROBE | CMD_MAC, None, 2)  # high 2
    accepts += await count_accepts_span(dut, CMD_MAC, None, 2)           # low 2
    accepts += await count_accepts_span(dut, STROBE | CMD_MAC, None, 3)  # high 3
    accepts += await count_accepts_span(dut, CMD_MAC, None, 4)           # settle

    golden = apply_command(golden, CMD_MAC, 0)  # exactly one MAC
    assert accepts == 1, f"ringing edge fired {accepts} accepts, want 1"
    await check_pins(dut, golden, "one MAC from a ringing edge")
    assert golden.acc == 42, "golden model self check failed"

    # The next legal command executes clean, the lockout has cleared.
    await command(dut, CMD_LDA, data=2)
    golden = apply_command(golden, CMD_LDA, 2)
    await command(dut, CMD_LDB, data=5)
    golden = apply_command(golden, CMD_LDB, 5)
    await command(dut, CMD_MAC)
    golden = apply_command(golden, CMD_MAC, 0)
    await check_pins(dut, golden, "clean MAC after the ringing edge")
    assert golden.acc == 52, "golden model self check failed"
