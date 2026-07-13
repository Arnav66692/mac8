# test_datapath.py
# cocotb tests for mac8_datapath. The contract is docs/SPEC.md, frozen v0.1.
# Drive discipline. Control pulses go high just after a clock edge and drop
# after exactly one rising edge samples them. All checks sample on falling
# edges, so values are settled and there is no read race.

import random
from dataclasses import dataclass, replace

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge
from cocotb.utils import get_sim_time

CLK_PERIOD_NS = 10

INT24_MAX = 8388607
INT24_MIN = -8388608

SEL_LO = 0
SEL_MID = 1
SEL_HI = 2
SEL_RSVD = 3

RANDOM_OPS = 2000
RANDOM_SEED = 20260713


def as_signed(value, bits):
    """Two's complement decode of an unsigned integer."""
    mask = (1 << bits) - 1
    value &= mask
    if value & (1 << (bits - 1)):
        return value - (1 << bits)
    return value


def sat24(x):
    """Exact saturation per SPEC.md. Returns the clamped value and a hit flag."""
    if x > INT24_MAX:
        return INT24_MAX, True
    if x < INT24_MIN:
        return INT24_MIN, True
    return x, False


@dataclass(frozen=True)
class Golden:
    """Golden model of the datapath state. Immutable, each op returns a new state."""

    a: int = 0
    b: int = 0
    acc: int = 0
    ovf: bool = False
    sel: int = SEL_LO

    def lda(self, byte):
        return replace(self, a=as_signed(byte, 8))

    def ldb(self, byte):
        return replace(self, b=as_signed(byte, 8))

    def mac(self):
        acc, hit = sat24(self.acc + self.a * self.b)
        return replace(self, acc=acc, ovf=self.ovf or hit)

    def clr(self):
        return replace(self, acc=0, ovf=False)

    def load_sel(self, sel):
        return replace(self, sel=sel & 0x3)

    def acc_byte(self):
        """Selected accumulator byte. Reserved encoding 11 reads the low byte."""
        shift = {SEL_LO: 0, SEL_MID: 8, SEL_HI: 16}.get(self.sel, 0)
        return ((self.acc & 0xFFFFFF) >> shift) & 0xFF


def dut_acc(dut):
    return as_signed(int(dut.acc_q.value), 24)


def clear_inputs(dut):
    dut.ld_a.value = 0
    dut.ld_b.value = 0
    dut.do_mac.value = 0
    dut.do_clr.value = 0
    dut.ld_sel.value = 0
    dut.sel_in.value = 0
    dut.data_in.value = 0


async def start_and_reset(dut):
    """Start the clock and apply synchronous reset for three cycles."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    clear_inputs(dut)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def pulse(dut, name, data=None, sel=None):
    """One clock control pulse. Exactly one rising edge samples it high."""
    if data is not None:
        dut.data_in.value = data & 0xFF
    if sel is not None:
        dut.sel_in.value = sel & 0x3
    sig = getattr(dut, name)
    sig.value = 1
    await RisingEdge(dut.clk)
    sig.value = 0


async def settle(dut):
    """Sample point. Falling edge, half a cycle after the active edge."""
    await FallingEdge(dut.clk)


def check(dut, golden, tag):
    """Compare architected state against the golden model."""
    acc = dut_acc(dut)
    ovf = int(dut.ovf.value)
    assert acc == golden.acc, f"{tag}. acc {acc}, expected {golden.acc}"
    assert ovf == int(golden.ovf), f"{tag}. ovf {ovf}, expected {int(golden.ovf)}"


@cocotb.test()
async def test_reset_values(dut):
    """Reset drives every register to 0 and selects the low byte."""
    await start_and_reset(dut)
    await settle(dut)
    assert dut_acc(dut) == 0, "acc not 0 after reset"
    assert int(dut.ovf.value) == 0, "ovf not 0 after reset"
    assert int(dut.out_byte.value) == 0, "out_byte not 0 after reset"
    assert as_signed(int(dut.a_q.value), 8) == 0, "A not 0 after reset"
    assert as_signed(int(dut.b_q.value), 8) == 0, "B not 0 after reset"
    assert int(dut.out_sel_q.value) == SEL_LO, "out_sel not low byte after reset"


@cocotb.test()
async def test_lda_ldb_latch(dut):
    """LDA and LDB latch data_in on their pulse and only then."""
    await start_and_reset(dut)

    await pulse(dut, "ld_a", data=0xA5)
    await settle(dut)
    assert as_signed(int(dut.a_q.value), 8) == -91, "LDA did not latch 0xA5"
    assert as_signed(int(dut.b_q.value), 8) == 0, "LDA disturbed B"

    await pulse(dut, "ld_b", data=0x7F)
    await settle(dut)
    assert as_signed(int(dut.b_q.value), 8) == 127, "LDB did not latch 0x7F"
    assert as_signed(int(dut.a_q.value), 8) == -91, "LDB disturbed A"

    dut.data_in.value = 0xFF
    await RisingEdge(dut.clk)
    await settle(dut)
    assert as_signed(int(dut.a_q.value), 8) == -91, "A latched without a pulse"
    assert as_signed(int(dut.b_q.value), 8) == 127, "B latched without a pulse"
    assert dut_acc(dut) == 0, "loads disturbed acc"


@cocotb.test()
async def test_single_mac_directed(dut):
    """Single MAC against the golden model. This window is the VCD reference."""
    await start_and_reset(dut)
    golden = Golden()
    t0 = get_sim_time("ns")

    await pulse(dut, "ld_a", data=0x35)
    golden = golden.lda(0x35)
    await pulse(dut, "ld_b", data=0xB9)
    golden = golden.ldb(0xB9)
    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)

    assert golden.acc == 53 * -71, "golden model self check failed"
    check(dut, golden, "single MAC 53 x -71")

    for sel in (SEL_LO, SEL_MID, SEL_HI):
        await pulse(dut, "ld_sel", sel=sel)
        golden = golden.load_sel(sel)
        await RisingEdge(dut.clk)
        await settle(dut)
        got = int(dut.out_byte.value)
        want = golden.acc_byte()
        assert got == want, f"readout sel {sel}. got {got:#04x}, want {want:#04x}"

    t1 = get_sim_time("ns")
    dut._log.info(f"directed MAC window in mac8_datapath.vcd. {t0} ns to {t1} ns")


@cocotb.test()
async def test_signed_corners(dut):
    """The three int8 corners. Minus 128 squared needs the full int16 range."""
    await start_and_reset(dut)
    golden = Golden()

    corners = [(-128, -128, 16384), (-128, 127, -16256), (127, 127, 16129)]
    for a, b, expect in corners:
        await pulse(dut, "do_clr")
        golden = golden.clr()
        await pulse(dut, "ld_a", data=a & 0xFF)
        golden = golden.lda(a)
        await pulse(dut, "ld_b", data=b & 0xFF)
        golden = golden.ldb(b)
        await pulse(dut, "do_mac")
        golden = golden.mac()
        await settle(dut)
        assert golden.acc == expect, "golden model self check failed"
        check(dut, golden, f"corner {a} x {b}")
        assert int(dut.ovf.value) == 0, f"corner {a} x {b} set ovf"


async def mac_until_saturated(dut, golden, a, b, tag):
    """Load operands, then MAC until the golden model saturates. Check each op."""
    await pulse(dut, "ld_a", data=a & 0xFF)
    golden = golden.lda(a)
    await pulse(dut, "ld_b", data=b & 0xFF)
    golden = golden.ldb(b)
    ops = 0
    while not golden.ovf:
        await pulse(dut, "do_mac")
        golden = golden.mac()
        ops += 1
        await settle(dut)
        check(dut, golden, f"{tag}, MAC {ops}")
    return golden, ops


@cocotb.test()
async def test_saturation_sticky(dut):
    """Both rails clamp. The flag sets on saturation and survives further MACs."""
    await start_and_reset(dut)
    golden = Golden()

    golden, ops = await mac_until_saturated(dut, golden, -128, -128, "positive rail")
    assert golden.acc == INT24_MAX, "golden model self check failed"
    assert dut_acc(dut) == INT24_MAX, "acc did not clamp at the positive rail"
    assert int(dut.ovf.value) == 1, "ovf not set at the positive rail"
    dut._log.info(f"positive rail hit after {ops} MACs")

    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    assert dut_acc(dut) == INT24_MAX, "acc moved past the positive rail"
    assert int(dut.ovf.value) == 1, "ovf dropped while clamped"

    await pulse(dut, "ld_a", data=1 & 0xFF)
    golden = golden.lda(1)
    await pulse(dut, "ld_b", data=(-1) & 0xFF)
    golden = golden.ldb(-1)
    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    check(dut, golden, "non saturating MAC after positive rail")
    assert int(dut.ovf.value) == 1, "sticky ovf did not survive a clean MAC"

    await pulse(dut, "do_clr")
    golden = golden.clr()
    await settle(dut)
    check(dut, golden, "CLR between rails")

    golden, ops = await mac_until_saturated(dut, golden, -128, 127, "negative rail")
    assert golden.acc == INT24_MIN, "golden model self check failed"
    assert dut_acc(dut) == INT24_MIN, "acc did not clamp at the negative rail"
    assert int(dut.ovf.value) == 1, "ovf not set at the negative rail"
    dut._log.info(f"negative rail hit after {ops} MACs")

    await pulse(dut, "ld_a", data=1 & 0xFF)
    golden = golden.lda(1)
    await pulse(dut, "ld_b", data=1 & 0xFF)
    golden = golden.ldb(1)
    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    check(dut, golden, "non saturating MAC after negative rail")
    assert int(dut.ovf.value) == 1, "sticky ovf did not survive a clean MAC"


@cocotb.test()
async def test_exact_rail_boundary(dut):
    """Landing exactly on a rail is not saturation. One step past it is.

    This pins the strict compares in the RTL. A clamp written with >= or <=
    passes every other test, because only ovf differs when the 25 bit sum
    equals a rail exactly. Found by mutation review."""
    await start_and_reset(dut)
    golden = Golden()

    # Positive rail. 520 x 16129 plus 1520 plus 7 equals 8388607 exactly.
    await pulse(dut, "ld_a", data=127)
    golden = golden.lda(127)
    await pulse(dut, "ld_b", data=127)
    golden = golden.ldb(127)
    for _ in range(520):
        await pulse(dut, "do_mac")
        golden = golden.mac()
    await pulse(dut, "ld_a", data=40)
    golden = golden.lda(40)
    await pulse(dut, "ld_b", data=38)
    golden = golden.ldb(38)
    await pulse(dut, "do_mac")
    golden = golden.mac()
    await pulse(dut, "ld_a", data=7)
    golden = golden.lda(7)
    await pulse(dut, "ld_b", data=1)
    golden = golden.ldb(1)
    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    assert golden.acc == INT24_MAX, "golden model self check failed"
    assert not golden.ovf, "golden model self check failed"
    check(dut, golden, "exact positive rail")
    assert int(dut.ovf.value) == 0, "ovf set on an exact positive rail landing"

    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    check(dut, golden, "one step past the positive rail")
    assert int(dut.ovf.value) == 1, "ovf not set one step past the positive rail"

    # Negative rail. 1024 x minus 8192 equals minus 8388608 exactly.
    await pulse(dut, "do_clr")
    golden = golden.clr()
    await pulse(dut, "ld_a", data=64)
    golden = golden.lda(64)
    await pulse(dut, "ld_b", data=(-128) & 0xFF)
    golden = golden.ldb(-128)
    for _ in range(1024):
        await pulse(dut, "do_mac")
        golden = golden.mac()
    await settle(dut)
    assert golden.acc == INT24_MIN, "golden model self check failed"
    assert not golden.ovf, "golden model self check failed"
    check(dut, golden, "exact negative rail")
    assert int(dut.ovf.value) == 0, "ovf set on an exact negative rail landing"

    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    check(dut, golden, "one step past the negative rail")
    assert int(dut.ovf.value) == 1, "ovf not set one step past the negative rail"


@cocotb.test()
async def test_clr_clears_acc_and_ovf(dut):
    """CLR zeroes acc and ovf. It leaves A, B, and the byte select alone."""
    await start_and_reset(dut)
    golden = Golden()

    await pulse(dut, "ld_sel", sel=SEL_MID)
    golden = golden.load_sel(SEL_MID)
    golden, _ = await mac_until_saturated(dut, golden, -128, -128, "setup")
    assert int(dut.ovf.value) == 1, "setup failed to set ovf"

    await pulse(dut, "do_clr")
    golden = golden.clr()
    await settle(dut)
    check(dut, golden, "after CLR")
    assert dut_acc(dut) == 0, "CLR left acc nonzero"
    assert int(dut.ovf.value) == 0, "CLR left ovf set"
    assert as_signed(int(dut.a_q.value), 8) == -128, "CLR disturbed A"
    assert as_signed(int(dut.b_q.value), 8) == -128, "CLR disturbed B"
    assert int(dut.out_sel_q.value) == SEL_MID, "CLR disturbed out_sel"

    await RisingEdge(dut.clk)
    await settle(dut)
    assert int(dut.out_byte.value) == 0, "out_byte not 0 one clock after CLR"


@cocotb.test()
async def test_out_sel_mux_and_lag(dut):
    """out_sel selects each byte. out_byte follows one clock later by design."""
    await start_and_reset(dut)
    golden = Golden()

    # Build acc = 0x01401B so all three bytes differ.
    await pulse(dut, "ld_a", data=(-128) & 0xFF)
    golden = golden.lda(-128)
    await pulse(dut, "ld_b", data=(-128) & 0xFF)
    golden = golden.ldb(-128)
    for _ in range(5):
        await pulse(dut, "do_mac")
        golden = golden.mac()
    await pulse(dut, "ld_a", data=3)
    golden = golden.lda(3)
    await pulse(dut, "ld_b", data=9)
    golden = golden.ldb(9)
    await pulse(dut, "do_mac")
    golden = golden.mac()
    await settle(dut)
    assert golden.acc == 0x01401B, "golden model self check failed"
    check(dut, golden, "acc build for mux test")

    # Settle into steady state on the low byte.
    await RisingEdge(dut.clk)
    await settle(dut)
    assert int(dut.out_byte.value) == golden.acc_byte(), "steady state low byte wrong"

    # Reserved encoding 11 must read the low byte, per the RTL contract.
    for sel in (SEL_MID, SEL_HI, SEL_LO, SEL_RSVD):
        shown_before = golden.acc_byte()
        await pulse(dut, "ld_sel", sel=sel)
        golden = golden.load_sel(sel)
        await settle(dut)
        got = int(dut.out_byte.value)
        assert got == shown_before, (
            f"sel {sel}. out_byte moved same cycle, got {got:#04x}, "
            f"expected old {shown_before:#04x}"
        )
        assert int(dut.out_sel_q.value) == sel, f"sel {sel} did not latch"
        await RisingEdge(dut.clk)
        await settle(dut)
        got = int(dut.out_byte.value)
        want = golden.acc_byte()
        assert got == want, f"sel {sel}. got {got:#04x}, want {want:#04x}"


def rand_byte():
    """Byte stream biased toward the int8 extremes so MACs can reach the rails."""
    roll = random.random()
    if roll < 0.15:
        return 0x80
    if roll < 0.30:
        return 0x7F
    return random.randrange(256)


@cocotb.test()
async def test_random_2000_ops(dut):
    """Random command mix against the golden model, out_byte lag included."""
    await start_and_reset(dut)
    golden = Golden()
    random.seed(RANDOM_SEED)

    # Weights. Loads and MACs dominate, CLR is rare so acc can reach the rails.
    ops = ["lda", "ldb", "mac", "clr", "sel", "nop"]
    weights = [20, 20, 30, 5, 10, 15]
    sat_events = 0

    for i in range(RANDOM_OPS):
        expected_out = golden.acc_byte()
        op = random.choices(ops, weights=weights)[0]
        data = rand_byte()
        dut.data_in.value = data

        if op == "lda":
            await pulse(dut, "ld_a", data=data)
            golden = golden.lda(data)
        elif op == "ldb":
            await pulse(dut, "ld_b", data=data)
            golden = golden.ldb(data)
        elif op == "mac":
            before = golden.ovf
            await pulse(dut, "do_mac")
            golden = golden.mac()
            sat_events += int(golden.ovf and not before)
        elif op == "clr":
            await pulse(dut, "do_clr")
            golden = golden.clr()
        elif op == "sel":
            sel = random.randrange(4)
            await pulse(dut, "ld_sel", sel=sel)
            golden = golden.load_sel(sel)
        else:
            await RisingEdge(dut.clk)

        await settle(dut)
        check(dut, golden, f"random op {i}, {op}")
        got = int(dut.out_byte.value)
        assert got == expected_out, (
            f"random op {i}, {op}. out_byte {got:#04x}, expected {expected_out:#04x}"
        )

    # Rails need about 512 same sign max products in a row. A random walk
    # cannot drift that far in 600 MACs, so rail coverage stays with the
    # directed saturation test. This log line records what the walk did hit.
    dut._log.info(
        f"{RANDOM_OPS} random ops done. final acc {golden.acc}, "
        f"ovf {int(golden.ovf)}, fresh saturation events {sat_events}"
    )
