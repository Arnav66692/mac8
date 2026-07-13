# test_top.py
# Protocol level tests for mac8_top. External ports only.
# The driver obeys the SPEC.md rules. Data and command first, then the
# strobe rise. Strobe high at least 3 core clocks, low at least 2 before
# the next rise. Data stable while the strobe is high plus 2 clocks after
# the fall. One helper performs a single command, every test builds on it.
# Checks sample on falling edges, so values are settled.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

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


async def start_and_reset(dut):
    """Start the clock and apply synchronous reset for three cycles."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def command(dut, cmd, data=0, high=3, low=2, setup=1):
    """One command per the spec driver rules.

    Data and command are written first, the strobe rises after them.
    With setup 0 the rise lands in the same window as the data write,
    which is the minimum legal profile. The command executes before this
    helper returns, so pins are stable for checks right after it."""
    dut.ui_in.value = data & 0xFF
    dut.uio_in.value = cmd & 0x7
    if setup:
        await ClockCycles(dut.clk, setup)
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
    Reads one internal signal, u_sync.accept, observation only."""
    while True:
        await FallingEdge(dut.clk)
        if int(dut.u_sync.accept.value) == 1:
            busy = (int(dut.uio_out.value) >> 4) & 1
            assert busy == 0, "accept fired while busy is high"


@cocotb.test()
async def test_reset_pin_state(dut):
    """Reset pin state. uo_out 0, busy 0, ovf 0, uio_oe 11110000."""
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
async def test_every_command_end_to_end(dut):
    """Every command code through the pins. NOP included."""
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


@cocotb.test()
async def test_dot_product_usage(dut):
    """Dot product of 24 elements per the spec usage section, then a
    saturating variant with the ovf pin checked."""
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
async def test_minimum_strobe_timing(dut):
    """Exactly 3 high and 2 low, 50 commands back to back, all correct.

    The data write and the strobe rise share one window, data written
    first, which is the minimum the driver rules allow."""
    await start_and_reset(dut)
    monitor = cocotb.start_soon(accept_busy_monitor(dut))
    golden = Golden()
    rng = random.Random(RANDOM_SEED + 1)

    for i in range(50):
        cmd = rng.randrange(8)
        data = rng.randrange(256)
        await command(dut, cmd, data=data, high=3, low=2, setup=0)
        golden = apply_command(golden, cmd, data)
        await check_pins(dut, golden, f"minimum timing command {i}, code {cmd}")

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


@cocotb.test()
async def test_random_protocol_500(dut):
    """500 random commands with random legal timing against the golden
    model, uo_out and the ovf pin checked after every command."""
    await start_and_reset(dut)
    monitor = cocotb.start_soon(accept_busy_monitor(dut))
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

    monitor.cancel()
    dut._log.info(f"{RANDOM_CMDS} random commands done. final acc {golden.acc}")


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
