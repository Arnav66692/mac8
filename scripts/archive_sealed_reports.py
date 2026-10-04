#!/usr/bin/env python3
"""Archive selected raw reports from the identified historical CI build."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEALED_SHA = "49f5f298692f274c6613cdc940e0cee991281943"
RAW_HASH = "5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("download", type=Path)
    parser.add_argument("--ci-record", type=Path, required=True)
    args = parser.parse_args()
    ci = json.loads(args.ci_record.read_text())
    if ci["headSha"] != SEALED_SHA or ci["databaseId"] != 29401092054 or ci["conclusion"] != "success":
        parser.error("CI record does not identify the sealed successful run")
    run = args.download / "GDS_logs/runs/wokwi"
    if digest(run / "final/nl/tt_um_arnav_mac8.nl.v") != RAW_HASH:
        parser.error("artifact netlist does not match the recorded seal")
    out = ROOT / "reports/sealed/29401092054"
    out.mkdir(parents=True, exist_ok=True)
    selected = [run / "final" / name for name in ("metrics.json", "metrics.csv", "commit_id.json")]
    selected += list((run / "final/sdc").glob("*.sdc"))
    selected += list((run / "55-openroad-stapostpnr").rglob("*.rpt"))
    for source in selected:
        destination = out / source.relative_to(run)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    precheck = args.download / "precheck_reports"
    shutil.copytree(precheck, out / "precheck", dirs_exist_ok=True)
    (out / "ci.json").write_text(json.dumps(ci, indent=2) + "\n")
    metrics = json.loads((out / "final/metrics.json").read_text())
    manifest = {
        "run_url": ci["url"], "run_id": ci["databaseId"], "source_commit": ci["headSha"],
        "historical_build": True, "portal_submission_status": "unverified",
        "raw_netlist_sha256": RAW_HASH,
        "powered_netlist_sha256": digest(run / "final/pnl/tt_um_arnav_mac8.pnl.v"),
        "gds_sha256": digest(run / "final/gds/tt_um_arnav_mac8.gds"),
        "standard_cells": metrics["design__instance__count__stdcell"],
        "setup_slack_ns": metrics["timing__setup__ws"],
        "hold_slack_ns": metrics["timing__hold__ws"],
        "utilization": metrics["design__instance__utilization"],
        "files_sha256": {str(path.relative_to(out)): digest(path)
                         for path in sorted(out.rglob("*")) if path.is_file() and path.name != "manifest.json"},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Archived", len(manifest["files_sha256"]), "reports from", ci["url"])


if __name__ == "__main__":
    main()
