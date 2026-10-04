#!/usr/bin/env python3
"""Reproducible cell-library mapping comparison. This is not routed PPA."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--liberty", type=Path, required=True)
    parser.add_argument("--yosys", default="yosys")
    args = parser.parse_args()
    liberty = args.liberty.resolve()
    if not liberty.is_file():
        parser.error("liberty does not exist")
    output = ROOT / "reports" / "dsp-demo" / "synthesis"
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text('{"status": "running", "metrics_available": false}\n')
    common = ["src/mac8_datapath.sv", "src/mac8_sync.sv", "src/mac8_rst_sync.sv", "src/mac8_ctrl.sv"]
    liberty_hash = hashlib.sha256(liberty.read_bytes()).hexdigest()
    results = {}
    for variant, top, extra in (
        ("baseline", "tt_um_arnav_mac8", "src/tt_um_arnav_mac8.sv"),
        ("fused", "tt_um_arnav_mac8_fused", "experiments/fused/tt_um_arnav_mac8_fused.sv"),
    ):
        sources = common + [extra]
        hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                  for name in sources + ["scripts/compare_synthesis.py"]}
        relative = output.relative_to(ROOT).as_posix()
        script = "\n".join([
            'read_liberty -lib "' + str(liberty) + '"',
            "read_verilog -sv -DSYNTHESIS " + " ".join(sources),
            "synth -top " + top + " -flatten -noabc",
            "delete t:$scopeinfo",
            'dfflibmap -liberty "' + str(liberty) + '"',
            'abc -liberty "' + str(liberty) + '" -D 20000',
            "clean",
            "check -assert",
            "tee -o " + relative + "/" + variant + '.json stat -json -liberty "' + str(liberty) + '"',
            "write_verilog -noattr " + relative + "/" + variant + ".v",
        ]) + "\n"
        script_path = output / (variant + ".ys")
        script_path.write_text(script)
        result = subprocess.run([args.yosys, "-Q", "-T", "-s", str(script_path)],
                                cwd=ROOT, text=True, capture_output=True)
        (output / (variant + ".log")).write_text(result.stdout + result.stderr)
        result.check_returncode()
        if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest for name, digest in hashes.items()) or hashlib.sha256(liberty.read_bytes()).hexdigest() != liberty_hash:
            raise RuntimeError("synthesis inputs changed during mapping")
        stats = json.loads((output / (variant + ".json")).read_text())
        module = stats["modules"]["\\" + top]
        unmapped = [name for name in module["num_cells_by_type"] if name.startswith("$")]
        if unmapped:
            raise RuntimeError("unmapped cells: " + str(unmapped))
        results[variant] = {"cells": module["num_cells"], "cell_area_um2": module["area"],
                            "source_sha256": hashes}
    results["status"] = "passed"
    results["method"] = {"stage": "synthesis library mapping, not place and route",
                         "yosys": subprocess.check_output([args.yosys, "-V"], text=True).strip(),
                         "liberty_name": liberty.name,
                         "liberty_sha256": liberty_hash,
                         "abc_delay_target_ps": 20000,
                         "area_source": "Liberty cell areas", "routed_timing": "not measured"}
    (output / "comparison.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
