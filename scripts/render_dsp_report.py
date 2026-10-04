#!/usr/bin/env python3
"""Build a local portfolio page from fresh, passing simulation evidence."""

import base64
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/dsp-demo"


def load(path):
    return json.loads((OUT / path).read_text())


def check_sources(record):
    for path, expected in record["source_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError("stale result for " + path + ", rerun its test")


def check_xml(path, expected):
    cases = list(ET.parse(ROOT / path).iter("testcase"))
    if len(cases) != expected or any(case.find(tag) is not None for case in cases
                                   for tag in ("failure", "error", "skipped")):
        raise RuntimeError("incomplete or failed regression: " + path)


def main():
    baseline, fused = load("baseline.json"), load("fused.json")
    for variant, record in (("baseline", baseline), ("fused", fused)):
        check_sources(record)
        soak = load(variant + "-soak.json")
        check_sources(soak)
        if record["mismatches"] or soak["mismatches"] or soak["scheduled_operations"] < 100000:
            raise RuntimeError("missing full passing command soak")
        check_xml("verification/results_" + variant + ".xml", 9)
    check_xml("verification/results_arithmetic.xml", 1)
    arithmetic = load("arithmetic.json")
    check_sources(arithmetic)
    if arithmetic["status"] != "passed" or arithmetic["operand_pairs"] != 65536:
        raise RuntimeError("missing exhaustive multiplication evidence")
    synthesis = load("synthesis/comparison.json")
    formal, mutations = load("formal/results.json"), load("mutations/results.json")
    for record in (synthesis, formal, mutations):
        if record.get("status") != "passed":
            raise RuntimeError("unfinished synthesis, proof or mutation run")
    check_sources(formal)
    check_sources(mutations)
    for variant in ("baseline", "fused"):
        check_sources(synthesis[variant])
    if baseline["raw_outputs"] != fused["raw_outputs"]:
        raise RuntimeError("candidate differs from baseline application")
    sealed_root = ROOT / "reports/sealed/29401092054"
    sealed = json.loads((sealed_root / "manifest.json").read_text())
    for path, expected in sealed["files_sha256"].items():
        if hashlib.sha256((sealed_root / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError("historical report hash mismatch: " + path)

    samples = np.array(baseline["samples"])
    filtered = np.array(baseline["raw_outputs"]) / 128
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.facecolor": "#111c2a", "figure.facecolor": "#111c2a",
                         "text.color": "#d9e7ef", "axes.labelcolor": "#97acbe",
                         "xtick.color": "#97acbe", "ytick.color": "#97acbe",
                         "axes.edgecolor": "#2a3c4c", "grid.color": "#263849"})
    figure, axes = plt.subplots(2, 1, figsize=(11, 6), constrained_layout=True)
    axes[0].plot(samples, color="#6b8196", linewidth=1.1, label="Input with interference")
    axes[0].plot(filtered, color="#59e3b4", linewidth=2, label="MAC8 output, host scaling")
    axes[0].set(xlabel="Sample", ylabel="Amplitude", title="16-tap FIR, captured from the RTL pins")
    axes[0].legend(facecolor="#111c2a", edgecolor="#2a3c4c", labelcolor="#d9e7ef")
    axes[0].grid(alpha=.45)
    # Full trace, including startup transient. No physical signal measurement.
    frequencies = np.fft.rfftfreq(len(samples))
    for values, color, label in ((samples, "#6b8196", "Input"), (filtered, "#59e3b4", "Output")):
        spectrum = np.abs(np.fft.rfft(values)) / len(values)
        axes[1].plot(frequencies, 20 * np.log10(np.maximum(spectrum, 1e-3)), color=color, label=label)
    axes[1].set(xlabel="Frequency, cycles per sample", ylabel="Amplitude, dB",
                title="Spectrum of the captured trace, including startup transient")
    axes[1].grid(alpha=.45)
    axes[1].legend(facecolor="#111c2a", edgecolor="#2a3c4c", labelcolor="#d9e7ef")
    figure.savefig(OUT / "fir-results.png", dpi=150)
    plt.close(figure)

    with (OUT / "fir-results.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["sample", "input", "baseline_acc24", "fused_acc24", "output_divided_by_128"])
        writer.writerows((i, sample, a, b, a / 128) for i, (sample, a, b) in
                        enumerate(zip(baseline["samples"], baseline["raw_outputs"], fused["raw_outputs"])))
    cycles_a, cycles_b = baseline["cycles_per_output"], fused["cycles_per_output"]
    reduction = 100 * (1 - cycles_b / cycles_a)
    area_a, area_b = synthesis["baseline"]["cell_area_um2"], synthesis["fused"]["cell_area_um2"]
    area_change = 100 * (area_b / area_a - 1)
    hero_path = ROOT.parent / "render/isometric.png"
    hero = base64.b64encode(hero_path.read_bytes()).decode() if hero_path.is_file() else ""
    manifest = {"status": "passed", "date_assessed": "2026-10-04",
                "baseline": baseline, "fused": fused,
                "cycle_reduction_percent": reduction,
                "synthesis_cell_area_change_percent": area_change,
                "formal_scope": formal["scope"], "mutation_results": mutations,
                "historical_build_url": sealed["run_url"],
                "portal_status": "unverified", "physical_demo": "not measured"}
    (OUT / "results.json").write_text(json.dumps(manifest, indent=2) + "\n")
    html = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MAC8 | Arnav Singh</title>
<style>
:root{color-scheme:dark;--bg:#0a111b;--card:#111c2a;--ink:#e9f0f5;--muted:#97acbe;--mint:#59e3b4;--line:#263849}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}
main{max-width:1180px;margin:auto;padding:32px}a{color:var(--mint)}a:focus-visible,button:focus-visible{outline:3px solid #ffd581;outline-offset:5px}
nav{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:13px;letter-spacing:.12em}.brand{color:var(--mint);font-weight:700}
.hero{display:grid;grid-template-columns:1.1fr 1fr;gap:35px;align-items:center;padding:56px 0 35px}h1{font-size:clamp(38px,5vw,65px);line-height:1.08;letter-spacing:-.045em;margin:15px 0 24px}h2{font-size:27px;letter-spacing:-.025em;margin-top:0}h3{font-size:18px}
.eyebrow{color:var(--mint);font-size:12px;font-weight:700;letter-spacing:.16em}.intro{color:var(--muted);max-width:600px}.chip{width:100%;border-radius:18px;border:1px solid var(--line)}.caption{font-size:12px;color:var(--muted)}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}.badge{border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:12px;color:var(--muted)}.badge.green{color:var(--mint)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.stat,.card{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:22px}.value{font-size:34px;font-weight:650;letter-spacing:-.04em;color:var(--mint)}.label{font-size:13px;color:var(--muted)}
section{margin-top:45px}.section-top{display:flex;justify-content:space-between;align-items:center;gap:20px}.section-top p{color:var(--muted)}.plot{width:100%;display:block;border:1px solid var(--line);border-radius:15px}
.two{display:grid;grid-template-columns:1.05fr 1fr;gap:18px}.flow{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:16px 0}.node{padding:14px;border-radius:9px;background:#172536;border:1px solid var(--line);font-size:13px}.node.chip-node{border-color:var(--mint);color:var(--mint)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 7px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}.positive{color:var(--mint)}
.switch{display:flex;gap:6px}button{border:1px solid var(--line);background:#172536;color:var(--muted);padding:8px 12px;border-radius:7px;font:inherit;font-size:13px;cursor:pointer}button[aria-pressed=true]{background:#143c32;color:var(--mint);border-color:var(--mint)}
.bar{height:14px;border-radius:4px;background:var(--mint);transition:width .25s}.track{background:#233548;border-radius:4px;margin:16px 0}.metric{font-size:30px;font-weight:650}ul{padding-left:20px}.muted{color:var(--muted)}.evidence a{display:block;margin:9px 0}.footer{margin:45px 0 12px;border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:13px}
@media(max-width:760px){main{padding:20px}.hero,.two{grid-template-columns:1fr}.hero{padding-top:35px}.stats{grid-template-columns:repeat(2,1fr)}.section-top{align-items:flex-start;flex-direction:column}.value{font-size:29px}nav{letter-spacing:.04em}}
@media(prefers-reduced-motion:reduce){.bar{transition:none}}
</style>
<main>
<nav><span class="brand">AS / MAC8</span><span>SYSTEMVERILOG · VERIFICATION · SKY130</span></nav>
<div class="hero"><div><div class="eyebrow">ARNAV SINGH · DIGITAL DESIGN</div><h1>INT8 compute,<br>verified from pins<br>to layout.</h1>
<p class="intro">A signed multiply-accumulate core with 24-bit saturation, a working FIR application, and a measured protocol optimization. Built with open ASIC tools and explicit verification boundaries.</p>
<div class="badges"><span class="badge green">Baseline hardened</span><span class="badge">DSP simulated</span><span class="badge">Fused candidate experimental</span></div></div>
<div><img class="chip" src="data:image/png;base64,@HERO@" alt="Isometric rendering of the actual baseline MAC8 GDS"><p class="caption">Actual baseline layout. Build 29401092054, SKY130, one Tiny Tapeout tile.</p></div></div>
<div class="stats"><div class="stat"><div class="value">65,536</div><div class="label">Signed operand pairs checked in RTL</div></div><div class="stat"><div class="value">200,000</div><div class="label">Scheduled operations across two RTL variants</div></div><div class="stat"><div class="value">@REDUCTION@%</div><div class="label">Fewer simulated cycles per FIR output</div></div><div class="stat"><div class="value">15 / 15</div><div class="label">Historical baseline prechecks passed</div></div></div>
<section><div class="section-top"><div><div class="eyebrow">APPLICATION</div><h2>Turn noisy samples into a useful signal.</h2></div><p>128 outputs per variant. Zero integer mismatches.</p></div><img class="plot" src="fir-results.png" alt="Captured noisy input, MAC8 filtered output, and their frequency spectra"><p class="caption">Host stores coefficients and sample history. MAC8 performs the arithmetic. The 16-tap filter introduces a 7.5-sample group delay. Plot values are from simulation; no physical throughput is claimed.</p></section>
<section class="two"><div class="card"><div class="eyebrow">ARCHITECTURE</div><h2>One multiplier. A precise contract.</h2><div class="flow" aria-label="Host samples and coefficients flow into MAC8, then three-byte readback"><div class="node">Host<br>samples + coefficients</div><span aria-hidden="true">→</span><div class="node chip-node">MAC8<br>8 × 8 → sat24</div><span aria-hidden="true">→</span><div class="node">Readback<br>3 bytes</div></div><p class="muted">The host supplies signed operands over an 8-bit bus. A synchronized strobe accepts commands. Sticky overflow records saturation. The output register exposes the selected accumulator byte.</p><a href="../../docs/BRINGUP.md">Driver and bring-up guide →</a></div>
<div class="card"><div class="section-top"><div class="eyebrow">CYCLE EXPERIMENT</div><div class="switch"><button type="button" id="baseline" aria-pressed="true">Baseline</button><button type="button" id="fused" aria-pressed="false">Fused</button></div></div><h2 id="variantTitle">Three commands per fresh pair</h2><div class="metric"><span id="cycles">@BASE_CYCLES@</span> cycles / FIR output</div><div class="track"><div id="bar" class="bar" style="width:100%"></div></div><p id="commands" class="muted">LDA → LDB → MAC. Includes CLR and full readback.</p><p class="caption">Same one-clock setup, three-clock strobe, three-clock low interval. 50 MHz assumed. Software GPIO overhead is excluded.</p></div></section>
<section><div class="eyebrow">RESULTS</div><h2>A tradeoff you can reproduce.</h2><div class="card"><table><thead><tr><th>Metric</th><th>Baseline</th><th>Fused candidate</th></tr></thead><tbody><tr><td>Simulated cycles / 16-tap output</td><td>@BASE_CYCLES@</td><td class="positive">@FUSED_CYCLES@</td></tr><tr><td>Equivalent outputs/s at assumed 50 MHz</td><td>@BASE_RATE@</td><td>@FUSED_RATE@</td></tr><tr><td>Mapped standard cells, local synthesis</td><td>@BASE_CELLS@</td><td>@FUSED_CELLS@</td></tr><tr><td>Mapped cell area, µm²</td><td>@BASE_AREA@</td><td>@FUSED_AREA@</td></tr><tr><td>Routed candidate timing and area</td><td colspan="2">Not measured in this local report. Experimental hardening runs separately.</td></tr></tbody></table><p class="caption">Local Yosys comparison uses the same SKY130 typical-corner Liberty and 20 ns ABC mapping target. Cell area changes by @AREA_CHANGE@%. Synthesis estimates are distinct from routed area, STA and silicon measurements.</p></div></section>
<section class="two"><div class="card"><div class="eyebrow">VERIFICATION</div><h2>Prove the scope. Break the protections.</h2><ul class="muted"><li>Exhaustive signed multiplication and exact FIR references.</li><li>Both saturation rails, sticky overflow, byte reads and reset recovery.</li><li>Fused scheduling invariants pass BMC and induction, with reachable covers.</li><li>Old-B, missing-MAC and stuck-low busy mutants are caught.</li><li>A missing pending-reset mutant fails the control proof.</li></ul><p class="caption">Formal scope covers scheduling and selected handshake properties. Arithmetic equivalence and physical metastability are outside those proofs.</p><a href="../../docs/VERIFICATION_MATRIX.md">Requirements and proof boundaries →</a></div><div class="card evidence"><div class="eyebrow">EVIDENCE</div><h2>Inspect the engineering.</h2><a href="results.json">Application results and source hashes</a><a href="fir-results.csv">Captured input and output CSV</a><a href="synthesis/comparison.json">Synthesis comparison</a><a href="../sealed/29401092054/manifest.json">Historical raw-report manifest</a><a href="../sealed/29401092054/precheck/results.md">15 baseline prechecks</a><a href="../../docs/OPTIMIZATION.md">Optimization method and resume wording</a><p class="caption">Baseline raw metrics: @SEALED_CELLS@ cells, +@SETUP@ ns setup, +@HOLD@ ns hold. Max-transition exceptions remain documented in W1. Portal submission status is unverified.</p></div></section>
<div class="footer">Generated from passing, source-matched artifacts. Simulation and synthesis results are labeled by stage. ASIC bring-up and measured system performance follow when hardware is available.</div>
</main><script>
const values={baseline:@BASE_CYCLES@,fused:@FUSED_CYCLES@};
for(const variant of Object.keys(values)){document.getElementById(variant).addEventListener('click',()=>{
document.getElementById('cycles').textContent=values[variant];
document.getElementById('bar').style.width=(100*values[variant]/values.baseline)+'%';
document.getElementById('variantTitle').textContent=variant==='baseline'?'Three commands per fresh pair':'Two commands per fresh pair';
document.getElementById('commands').textContent=variant==='baseline'?'LDA → LDB → MAC. Includes CLR and full readback.':'LDA → LDB_MAC. B is loaded before the delayed MAC.';
for(const key of Object.keys(values))document.getElementById(key).setAttribute('aria-pressed',String(key===variant));
});}
</script></html>'''
    replacements = {"HERO": hero, "REDUCTION": f"{reduction:.1f}", "BASE_CYCLES": str(cycles_a),
                    "FUSED_CYCLES": str(cycles_b), "BASE_RATE": f"{baseline['equivalent_outputs_per_second']:,.0f}",
                    "FUSED_RATE": f"{fused['equivalent_outputs_per_second']:,.0f}",
                    "BASE_CELLS": str(synthesis["baseline"]["cells"]), "FUSED_CELLS": str(synthesis["fused"]["cells"]),
                    "BASE_AREA": f"{area_a:,.1f}", "FUSED_AREA": f"{area_b:,.1f}", "AREA_CHANGE": f"{area_change:.2f}",
                    "SEALED_CELLS": str(sealed["standard_cells"]), "SETUP": f"{sealed['setup_slack_ns']:.3f}",
                    "HOLD": f"{sealed['hold_slack_ns']:.3f}"}
    for key, value in replacements.items():
        html = html.replace("@" + key + "@", value)
    (OUT / "index.html").write_text(html)
    print("Generated", OUT / "index.html")


if __name__ == "__main__":
    main()
