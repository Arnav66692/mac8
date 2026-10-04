#!/usr/bin/env python3
"""Kill fused datapath and busy mistakes using fresh, isolated builds."""

import json
import hashlib
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    results = {}
    source_paths = [str(path.relative_to(ROOT)) for folder in ("app", "src", "experiments", "verification")
                    for path in (ROOT / folder).rglob("*")
                    if path.suffix in (".py", ".sv") and "sim_build" not in str(path)]
    source_paths += ["verification/Makefile", "scripts/check_app_mutations.py"]
    source_hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source_paths}
    mutations = {
        "old_b_operand": ("ld_b = ld_b_base | fused_fire;", "ld_b = ld_b_base;"),
        "missing_fused_mac": ("do_mac = do_mac_base | pending;", "do_mac = do_mac_base;"),
        "busy_stuck_low": ("{2'b00, ovf, busy, 4'b0000}", "{2'b00, ovf, 1'b0, 4'b0000}"),
    }
    out = ROOT / "reports/dsp-demo/mutations"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text('{"status": "running"}\n')
    for name in ("control", "busy_control", *mutations):
        with tempfile.TemporaryDirectory(prefix="mac8-mutation-") as temporary:
            scratch = Path(temporary)
            for folder in ("app", "src", "experiments", "verification"):
                shutil.copytree(ROOT / folder, scratch / folder,
                                ignore=shutil.ignore_patterns("sim_build*", "results*", "__pycache__"))
            if name in mutations:
                rtl = scratch / "experiments/fused/tt_um_arnav_mac8_fused.sv"
                original = rtl.read_text()
                old, new = mutations[name]
                if original.count(old) != 1:
                    raise RuntimeError("mutation target drifted: " + name)
                rtl.write_text(original.replace(old, new))
            selected = "test_busy_pin_contract" if name in ("busy_control", "busy_stuck_low") else "test_signed_vectors_and_new_b"
            environment = dict(os.environ, COCOTB_TEST_FILTER=selected)
            result = subprocess.run(["make", "VARIANT=fused"], cwd=scratch / "verification",
                                    env=environment, text=True, capture_output=True, timeout=120)
            (out / (name + ".log")).write_text(result.stdout + result.stderr)
            xml = scratch / "verification/results_fused.xml"
            if not xml.is_file():
                raise RuntimeError("missing results, infrastructure failure: " + name)
            tree = ET.parse(xml)
            cases = [case for case in tree.iter("testcase") if case.find("skipped") is None]
            if len(cases) != 1 or any(case.find("error") is not None for case in cases):
                raise RuntimeError("unexpected test count or infrastructure error: " + name)
            failed = any(case.find("failure") is not None for case in cases)
            if failed != (name in mutations) or (result.returncode == 0) == failed:
                raise RuntimeError("mutation gate did not hold: " + name)
            results[name] = "caught" if failed else "passed"
    results["status"] = "passed"
    results["source_sha256"] = source_hashes
    if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest for path, digest in source_hashes.items()):
        raise RuntimeError("sources changed during mutation run")
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
