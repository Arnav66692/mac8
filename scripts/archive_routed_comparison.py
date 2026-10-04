#!/usr/bin/env python3
"""Archive same-commit hardening artifacts and compare their actual metrics."""

import argparse
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for variant in ("baseline", "fused"):
        parser.add_argument("--" + variant, type=Path, required=True)
        parser.add_argument("--" + variant + "-ci", type=Path, required=True)
    parser.add_argument("--fused-gate", type=Path, required=True)
    args = parser.parse_args()
    comparison = {}
    result_path = ROOT / "reports/dsp-demo/routed-comparison.json"
    result_path.write_text('{"status": "running"}\n')
    configs, pdks, commits = [], [], []
    for variant in ("baseline", "fused"):
        download = getattr(args, variant)
        ci = json.loads(getattr(args, variant + "_ci").read_text())
        if ci["status"] != "completed" or ci["conclusion"] != "success":
            raise RuntimeError("CI is unfinished or failed: " + variant)
        commits.append(ci["headSha"])
        run = download / "GDS_logs/runs/wokwi"
        package = download / "tt_submission/tt_submission"
        for identity_path in (run / "final/commit_id.json", package / "commit_id.json"):
            identity = json.loads(identity_path.read_text())
            if identity["commit"] != ci["headSha"] or identity["workflow_url"] != ci["url"]:
                raise RuntimeError("download does not belong to the supplied CI run")
        pdk = json.loads((package / "pdk.json").read_text())
        pdks.append(pdk)
        sta = next(run.glob("*-openroad-stapostpnr"))
        config = json.loads((sta / "config.json").read_text())
        top = "tt_um_arnav_mac8" + ("_fused" if variant == "fused" else "")
        if config.pop("DESIGN_NAME") != top:
            raise RuntimeError("wrong design in artifact")
        configs.append(config)
        out = ROOT / "reports/routed" / str(ci["databaseId"])
        out.mkdir(parents=True, exist_ok=True)
        selected = [run / "final" / filename for filename in ("metrics.json", "commit_id.json")]
        selected += list((run / "final").glob("sdc/*.sdc"))
        for kind in ("nl", "pnl", "gds"):
            selected += list((run / "final" / kind).glob("*"))
        selected += list((run / "final/sdf/max_ss_100C_1v60").glob("*.sdf"))
        selected += [sta / "config.json", sta / "summary.rpt"]
        for filename in ("checks.rpt", "ws.max.rpt", "ws.min.rpt", "tns.max.rpt", "tns.min.rpt"):
            selected += list(sta.glob("*/" + filename))
        source_hashes = {}
        for filename in ("mac8_datapath.sv", "mac8_ctrl.sv", "mac8_sync.sv", "mac8_rst_sync.sv", top + ".sv"):
            local = ROOT / ("experiments/fused" if variant == "fused" and filename == top + ".sv" else "src") / filename
            if digest(local) != digest(download / "tt_submission/src" / filename):
                raise RuntimeError("artifact source differs from local source: " + filename)
            source_hashes[str(local.relative_to(ROOT))] = digest(local)
        for source in selected:
            target = out / source.relative_to(run)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(package / "pdk.json", out / "pdk.json")
        shutil.copytree(download / "precheck_reports", out / "precheck", dirs_exist_ok=True)
        cases = list(ET.parse(out / "precheck/results.xml").iter("testcase"))
        if len(cases) != 15 or any(case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")):
            raise RuntimeError("precheck was incomplete or failed")
        (out / "ci.json").write_text(json.dumps(ci, indent=2) + "\n")
        metrics = json.loads((run / "final/metrics.json").read_text())
        corners = {corner: {"setup_slack_ns": metrics["timing__setup__ws__corner:" + corner],
                            "hold_slack_ns": metrics["timing__hold__ws__corner:" + corner],
                            "transition_violations": metrics["design__max_slew_violation__count__corner:" + corner]}
                   for corner in config["STA_CORNERS"]}
        if len(corners) != 9 or any(row["setup_slack_ns"] < 0 or row["hold_slack_ns"] < 0 for row in corners.values()):
            raise RuntimeError("setup or hold failed, or corners incomplete")
        if any(metrics[key] != 0 for key in ("magic__drc_error__count", "route__drc_errors", "design__lvs_error__count", "antenna__violating__nets", "antenna__violating__pins")):
            raise RuntimeError("implementation checks contain errors")
        record = {"run_id": ci["databaseId"], "run_url": ci["url"], "source_commit": ci["headSha"],
                  "source_sha256": source_hashes, "standard_cells": metrics["design__instance__count__stdcell"],
                  "cell_area_um2": metrics["design__instance__area__stdcell"],
                  "utilization": metrics["design__instance__utilization"], "corners": corners,
                  "setup_slack_ns": metrics["timing__setup__ws"], "hold_slack_ns": metrics["timing__hold__ws"],
                  "max_transition_violations": metrics["design__max_slew_violation__count"],
                  "max_capacitance_violations": metrics["design__max_cap_violation__count"],
                  "drc": metrics["magic__drc_error__count"], "lvs": metrics["design__lvs_error__count"],
                  "antenna_nets": metrics["antenna__violating__nets"], "prechecks_passed": len(cases),
                  "pdk": pdk, "artifact_sha256": {kind: digest(run / "final" / kind / (top + "." + (kind + ".v" if kind != "gds" else "gds")))
                                                  for kind in ("nl", "pnl", "gds")}}
        if variant == "fused":
            gate = json.loads((args.fused_gate / "reports/dsp-demo/fused-gate.json").read_text())
            soak = json.loads((args.fused_gate / "reports/dsp-demo/fused-gate-soak.json").read_text())
            xml = args.fused_gate / "verification/results_fused-gate.xml"
            gate_cases = list(ET.parse(xml).iter("testcase"))
            if len(gate_cases) != 9 or any(case.find(tag) is not None for case in gate_cases for tag in ("failure", "error", "skipped")):
                raise RuntimeError("candidate application regression incomplete")
            if gate["mismatches"] or soak["mismatches"] or soak["scheduled_operations"] < 100000:
                raise RuntimeError("candidate gate workload incomplete")
            for evidence in (gate, soak):
                for path, expected in evidence["source_sha256"].items():
                    actual = record["artifact_sha256"]["pnl"] if path == "test/gate_level_netlist.v" else digest(ROOT / path)
                    if actual != expected:
                        raise RuntimeError("candidate application source or netlist mismatch")
            record["application_tests_passed"] = len(gate_cases)
            record["application_scheduled_operations"] = soak["scheduled_operations"]
            shutil.copytree(args.fused_gate, out / "application", dirs_exist_ok=True)
        record["files_sha256"] = {str(path.relative_to(out)): digest(path) for path in sorted(out.rglob("*"))
                                   if path.is_file() and path.name != "manifest.json"}
        (out / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
        comparison[variant] = record
    if commits[0] != commits[1] or configs[0] != configs[1] or pdks[0] != pdks[1]:
        raise RuntimeError("source commit, flow configuration or PDK differs")
    comparison["same_configuration_except_design_name"] = True
    comparison["status"] = "measured"
    comparison["cell_area_change_percent"] = 100 * (comparison["fused"]["cell_area_um2"] / comparison["baseline"]["cell_area_um2"] - 1)
    comparison["disposition"] = "Experimental. Setup and hold meet, transition exceptions require a separate review."
    result_path.write_text(json.dumps(comparison, indent=2) + "\n")
    print("Archived routed comparison:", result_path)


if __name__ == "__main__":
    main()
