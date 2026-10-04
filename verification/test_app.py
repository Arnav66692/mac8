"""Application regression using only external chip pins."""

import json
import hashlib
import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

from app.driver import CLR, LDA, LDB, MAC, LDB_MAC, Mac8Driver
from app.reference import COEFFICIENTS, dot_reference, fir_reference, noisy_signal

VARIANT = os.environ.get("MAC8_VARIANT", "baseline")
CLOCK_NS = 20
ROOT = Path("..").resolve()


def source_hashes():
    paths = ["app/driver.py", "app/reference.py", "verification/test_app.py",
             "verification/Makefile", "verification/tb_app.sv"]
    if VARIANT.endswith("gate"):
        paths += ["test/gate_level_netlist.v"]
    else:
        paths += ["src/mac8_datapath.sv", "src/mac8_sync.sv", "src/mac8_rst_sync.sv", "src/mac8_ctrl.sv"]
        paths += ["experiments/fused/tt_um_arnav_mac8_fused.sv" if VARIANT == "fused" else "src/tt_um_arnav_mac8.sv"]
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


SOURCE_HASHES = source_hashes()


class PinBackend:
    def __init__(self, dut):
        self.dut = dut

    def write_inputs(self, data, control):
        self.dut.ui_in.value = data
        self.dut.uio_in.value = control

    def set_reset(self, released):
        self.dut.rst_n.value = int(released)

    async def wait_cycles(self, clocks):
        await Timer(clocks * CLOCK_NS, unit="ns")

    def read_byte(self):
        return int(self.dut.uo_out.value)

    def read_status(self):
        return int(self.dut.uio_out.value)


async def start(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start())
    driver = Mac8Driver(PinBackend(dut), fused=VARIANT.startswith("fused"))
    await driver.reset()
    assert int(dut.uio_oe.value) == 0xF0
    return driver


@cocotb.test()
async def test_signed_vectors_and_new_b(dut):
    driver = await start(dut)
    for xs, ws in (([-128, 127, -1, 0, 1], [-128, -128, 127, -1, 127]),
                   ([7, 7, 7, 7], [1, -2, 3, -4]), ([], [])):
        assert await driver.dot_product(xs, ws) == dot_reference(xs, ws)


@cocotb.test()
async def test_fir_impulse_step_and_alternation(dut):
    driver = await start(dut)
    for samples in ([127] + [0] * 19, [37] * 20, [-128, 127] * 10):
        assert await driver.fir(samples, COEFFICIENTS) == fir_reference(samples)


@cocotb.test()
async def test_saturation_sticky_and_clear(dut):
    driver = await start(dut)
    for xs, ws in (([-128] * 512, [-128] * 512), ([-128] * 517, [127] * 517)):
        assert await driver.dot_product(xs, ws) == dot_reference(xs, ws)
        await driver.command(LDA, 0)
        await driver.command(MAC)
        _, overflow = await driver.read_accumulator()
        assert overflow, "overflow must remain sticky"
        await driver.command(CLR)
        assert await driver.read_accumulator() == (0, False)


@cocotb.test()
async def test_reset_recovery(dut):
    driver = await start(dut)
    assert await driver.dot_product([7], [-9]) == (-63, False)
    await driver.reset()
    assert await driver.read_accumulator() == (0, False)
    assert await driver.dot_product([-128], [-128]) == (16384, False)


@cocotb.test()
async def test_command_hold_and_read_margin(dut):
    driver = await start(dut)
    # The shortest configurable driver timing still holds input data after
    # strobe falls and samples each result at least five clocks after rise.
    for high, low in ((3, 2), (3, 3), (5, 4)):
        timed = Mac8Driver(driver.backend, fused=driver.fused,
                           high_cycles=high, low_cycles=low)
        assert await timed.dot_product([100, -128], [100, 127]) == (-6256, False)


@cocotb.test()
async def test_random_vectors(dut):
    driver = await start(dut)
    rng = random.Random(0x4D414338)
    for size in (1, 2, 7, 16, 64, 511):
        xs = [rng.randrange(-128, 128) for _ in range(size)]
        ws = [rng.randrange(-128, 128) for _ in range(size)]
        assert await driver.dot_product(xs, ws) == dot_reference(xs, ws)


@cocotb.test()
async def test_busy_pin_contract(dut):
    driver = await start(dut)
    await driver.command(LDA, 7)
    await driver.command(LDB, 9)
    for opcode, expected in ((MAC, 1), (LDA, 0), (0, 2 if driver.fused else 0)):
        task = cocotb.start_soon(driver.command(opcode, 3))
        await Timer(5, unit="ns")
        busy_cycles = 0
        for _ in range(10):
            busy_cycles += bool(driver.backend.read_status() & 0x10)
            await Timer(CLOCK_NS, unit="ns")
        await task
        assert busy_cycles == expected, f"opcode {opcode}: busy high {busy_cycles}, expected {expected}"
        assert not driver.backend.read_status() & 0x10


@cocotb.test()
async def test_fir_demo_and_cycle_measurement(dut):
    driver = await start(dut)
    samples = noisy_signal()
    expected = fir_reference(samples)
    commands_before = driver.commands
    start_ns = get_sim_time(unit="ns")
    raw = await driver.fir(samples, COEFFICIENTS)
    elapsed_ns = get_sim_time(unit="ns") - start_ns
    assert raw == expected
    commands = driver.commands - commands_before
    expected_per_output = (2 if driver.fused else 3) * 16 + 4
    assert commands == len(samples) * expected_per_output
    assert elapsed_ns / CLOCK_NS == commands * 7
    result = {
        "backend": "functional gate-level simulation" if VARIANT.endswith("gate") else "RTL simulation",
        "variant": VARIANT, "source_sha256": SOURCE_HASHES,
        "clock_hz_assumed": 50000000, "samples": samples,
        "coefficients": list(COEFFICIENTS), "raw_outputs": raw,
        "reference_outputs": expected, "mismatches": 0,
        "commands": commands, "simulated_cycles": int(elapsed_ns / CLOCK_NS),
        "cycles_per_output": int(elapsed_ns / CLOCK_NS / len(samples)),
        "equivalent_outputs_per_second": len(samples) * 1e9 / elapsed_ns,
        "timing": {"setup": 1, "high": 3, "low": 3},
    }
    output = Path("../reports/dsp-demo")
    output.mkdir(parents=True, exist_ok=True)
    assert source_hashes() == SOURCE_HASHES, "sources changed during simulation"
    (output / (VARIANT + ".json")).write_text(json.dumps(result, indent=2) + "\n")


@cocotb.test()
async def test_seeded_command_soak(dut):
    driver = await start(dut)
    rng = random.Random(0x534F414B)
    count = int(os.environ.get("MAC8_SOAK_COMMANDS", "100000"))
    assert count >= 1000
    # Independent architected state. Read periodically and after each clear.
    a = b = acc = 0
    overflow = False
    bins = {"opcodes": [0] * 8, "positive_saturation": 0, "negative_saturation": 0,
            "sticky_clear": 0, "reset": 0, "read_bytes": [0] * 3}
    for index in range(count):
        if index and index % 25000 == 0:
            await driver.reset()
            a = b = acc = 0
            overflow = False
            bins["reset"] += 1
        # Long repeated extreme products intentionally reach both rails.
        block = index // 1000
        offset = index % 1000
        if offset == 0:
            opcode, data = CLR, 0
        elif offset == 1:
            opcode, data = LDA, 128
        elif offset == 2:
            opcode, data = LDB, (128 if block % 2 == 0 else 127)
        elif offset < 650:
            opcode, data = MAC, 0
        else:
            opcode, data = rng.randrange(8), rng.randrange(256)
        await driver.command(opcode, data)
        bins["opcodes"][opcode] += 1
        signed = data if data < 128 else data - 256
        if opcode == CLR:
            bins["sticky_clear"] += int(overflow)
            acc, overflow = 0, False
        elif opcode == LDA:
            a = signed
        elif opcode == LDB:
            b = signed
        if driver.fused and opcode == LDB_MAC:
            b = signed
        if opcode == MAC or (driver.fused and opcode == LDB_MAC):
            candidate = acc + a * b
            if candidate > 8388607:
                bins["positive_saturation"] += 1
            if candidate < -8388608:
                bins["negative_saturation"] += 1
            overflow |= not -8388608 <= candidate <= 8388607
            acc = min(8388607, max(-8388608, candidate))
        if opcode >= 5:
            bins["read_bytes"][opcode - 5] += 1
            assert driver.backend.read_byte() == ((acc & 0xFFFFFF) >> (8 * (opcode - 5))) & 255
        if index % 997 == 0 or opcode == CLR:
            assert await driver.read_accumulator() == (acc, overflow)
    assert await driver.read_accumulator() == (acc, overflow)
    assert all(bins["opcodes"]) and all(bins["read_bytes"])
    assert bins["positive_saturation"] and bins["negative_saturation"] and bins["sticky_clear"]
    if count > 25000:
        assert bins["reset"]
    result = {"variant": VARIANT, "seed": "0x534f414b", "scheduled_operations": count,
              "mismatches": 0, "functional_bins": bins, "source_sha256": SOURCE_HASHES}
    output = Path("../reports/dsp-demo")
    output.mkdir(parents=True, exist_ok=True)
    assert source_hashes() == SOURCE_HASHES, "sources changed during simulation"
    (output / (VARIANT + "-soak.json")).write_text(json.dumps(result, indent=2) + "\n")
