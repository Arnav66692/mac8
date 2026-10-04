"""Exhaustive white-box multiplication check on the actual datapath RTL."""

import cocotb
import hashlib
import json
from pathlib import Path
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer


@cocotb.test()
async def test_all_signed_operand_pairs(dut):
    root = Path(__file__).resolve().parents[1]
    paths = ("src/mac8_datapath.sv", "verification/test_arithmetic.py", "verification/arithmetic.mk")
    hashes = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}
    for name in ("ld_a", "ld_b", "do_mac", "do_clr", "ld_sel", "sel_in", "data_in"):
        getattr(dut, name).value = 0
    dut.rst_n.value = 0
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    for a in range(-128, 128):
        dut.ld_a.value = 1
        dut.data_in.value = a & 255
        await FallingEdge(dut.clk)
        dut.ld_a.value = 0
        for b in range(-128, 128):
            dut.ld_b.value = 1
            dut.data_in.value = b & 255
            await FallingEdge(dut.clk)
            await Timer(1, unit="ps")
            actual = dut.product.value.to_signed()
            assert actual == a * b, f"{a} * {b}: {actual}"
        dut.ld_b.value = 0
    assert all(hashlib.sha256((root / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    out = root / "reports/dsp-demo/arithmetic.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"status": "passed", "operand_pairs": 65536, "source_sha256": hashes}, indent=2) + "\n")
