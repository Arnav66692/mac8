#!/usr/bin/env python3
"""Prove the candidate's scheduling invariants and exercise its covers."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(argv, logfile, expected="PASSED"):
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=180)
    text = result.stdout + result.stderr
    logfile.write_text(text)
    if expected is None:
        result.check_returncode()
    elif "Status: " + expected not in text or result.returncode != (0 if expected == "PASSED" else 1):
        raise RuntimeError("unexpected solver status, see " + str(logfile))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=20)
    args = parser.parse_args()
    if args.depth < 3:
        parser.error("depth must be at least three")
    out = ROOT / "reports/dsp-demo/formal"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text('{"status": "running"}\n')
    sources = "src/mac8_datapath.sv src/mac8_sync.sv src/mac8_rst_sync.sv src/mac8_ctrl.sv"
    fused = ROOT / "experiments/fused/tt_um_arnav_mac8_fused.sv"
    original = fused.read_text()
    source_paths = [*sources.split(), str(fused.relative_to(ROOT)), "scripts/check_fused_control.py"]
    source_hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source_paths}
    results = {}
    for name, source in (("base", original),
                         ("missing_pending_reset", original.replace("pending <= 1'b0;", "pending <= fused_fire;"))):
        if name != "base" and source == original:
            raise RuntimeError("mutation did not apply")
        (out / (name + ".sv")).write_text(source)
        prefix = "reports/dsp-demo/formal/" + name
        command = "read_verilog -formal -sv -DSYNTHESIS " + sources + " " + prefix + ".sv; "
        command += "prep -top tt_um_arnav_mac8_fused; flatten; async2sync; opt_clean; "
        command += "write_smt2 -wires " + prefix + ".smt2"
        run(["yosys", "-q", "-p", command], out / (name + ".yosys.log"), None)
        expected = "PASSED" if name == "base" else "FAILED"
        run(["yosys-smtbmc", "-s", "z3", "-t", str(args.depth), prefix + ".smt2"],
            out / (name + ".bmc.log"), expected)
        results[name] = expected
        if name == "base":
            for mode, flag in (("induction", "-i"), ("covers", "-c")):
                run(["yosys-smtbmc", "-s", "z3", flag, "-t", str(args.depth), prefix + ".smt2"],
                    out / (name + "." + mode + ".log"))
                results[mode] = "PASSED"
    results["scope"] = "pending scheduling, reset cancellation, pulse exclusion; not arithmetic equivalence or physical CDC"
    results["status"] = "passed"
    results["source_sha256"] = source_hashes
    if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest for path, digest in source_hashes.items()):
        raise RuntimeError("sources changed during proof run")
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
