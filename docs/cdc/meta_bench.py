#!/usr/bin/env python3
# Metastability extraction bench, single ngspice session. Structure per Beer
# and Ginosar. A fixed clock edge, the D edge time is the swept parameter.
# The device models are parsed once, then a control loop reruns the transient
# for each D edge time, so the cost is one parse plus many fast sims.
#
# Emits a CSV of offset from the balance point versus Q resolution time.
# No tau fit, no plot, no MTBF text. Those are Arnav's.

import os
import subprocess
import sys
import glob
import tempfile

PDK_ROOT = os.environ.get("PDK_ROOT", os.path.expanduser("~/.volare"))
LIB = os.path.join(PDK_ROOT, "sky130A", "libs.tech", "ngspice", "sky130.lib.spice")
CELL = os.environ["CELL_SPICE"]  # the extracted dfxtp_2 subckt
NGSPICE = os.environ.get("NGSPICE", "/opt/homebrew/bin/ngspice")
SUBCKT = "sky130_fd_sc_hd__dfxtp_2"  # the exact ff1 cell, item 1

CORNERS = {"tt": (1.80, 25, "tt"), "ss": (1.60, 100, "ss")}
TCLK = 20.0e-9
TSTOP = 30.0e-9
DSTEP = 5.0e-12


def build_deck(corner, td_list, outdir):
    vdd, temp, section = CORNERS[corner]
    # One deck, models parsed once. alterparam td then reset then tran per point.
    lines = [
        f"* metastability sweep {SUBCKT} {corner}, one session",
        f'.include "{CELL}"',
        f'.lib "{LIB}" {section}',
        "",
        f".param td=20n",
        f"Vpwr VPWR 0 {vdd}",
        "Vgnd VGND 0 0",
        f"Vpb  VPB  0 {vdd}",
        "Vnb  VNB  0 0",
        f"Vclk CLK 0 PWL(0 0 {TCLK:.6e} 0 {TCLK+20e-12:.6e} {vdd})",
        "Vd   D 0 PWL(0 0 {td} 0 {td+20p} " + f"{vdd})",
        f"Xdut CLK D VGND VNB VPB VPWR Q {SUBCKT}",
        "Cload Q 0 5f",
        f".options temp={temp}",
        ".control",
    ]
    for i, td in enumerate(td_list):
        out = os.path.join(outdir, f"q_{i:04d}.txt")
        lines += [
            f"alterparam td={td:.6e}",
            "reset",
            f"tran {DSTEP:.2e} {TSTOP:.2e} uic",
            f"wrdata {out} v(Q)",
        ]
    lines += [".endc", ".end", ""]
    return "\n".join(lines)


def read_pts(path):
    pts = []
    if os.path.exists(path):
        for line in open(path):
            p = line.split()
            if len(p) >= 2:
                try:
                    pts.append((float(p[0]), float(p[1])))
                except ValueError:
                    pass
    return pts


def resolution_ns(pts, vdd):
    hi, lo = 0.9 * vdd, 0.1 * vdd
    for t, v in pts:
        if t >= TCLK and (v >= hi or v <= lo):
            return (t - TCLK) * 1e9
    return (TSTOP - TCLK) * 1e9


def main():
    corner = sys.argv[1] if len(sys.argv) > 1 else "tt"
    vdd = CORNERS[corner][0]
    outdir = tempfile.mkdtemp(prefix="metasweep_")
    # Zoom on the balance found by the 1 ps pass, 19.9765 ns at tt, with
    # femtosecond steps so the metastable resolution tail can appear.
    center = float(os.environ.get("BAL_CENTER", "19.9765e-9"))
    step = float(os.environ.get("BAL_STEP", "5e-15"))
    npts = int(os.environ.get("BAL_NPTS", "120"))
    td_list = [center + k * step for k in range(-npts // 2, npts // 2 + 1)]
    deck = build_deck(corner, td_list, outdir)
    deckpath = os.path.join(outdir, "sweep.sp")
    open(deckpath, "w").write(deck)
    sys.stderr.write(f"running {len(td_list)} points in one session...\n")
    subprocess.run([NGSPICE, "-b", deckpath], capture_output=True, text=True, timeout=1200)

    rows = []
    for i, td in enumerate(td_list):
        pts = read_pts(os.path.join(outdir, f"q_{i:04d}.txt"))
        if not pts:
            continue
        fq = pts[-1][1] / vdd
        rt = resolution_ns(pts, vdd)
        rows.append((td, fq, rt))

    # Balance point, where final Q crosses 0.5, linear interpolation.
    balance = None
    for a, b in zip(rows, rows[1:]):
        if (a[1] - 0.5) * (b[1] - 0.5) < 0:
            frac = (0.5 - a[1]) / (b[1] - a[1])
            balance = a[0] + frac * (b[0] - a[0])
            break
    if balance is None:
        sys.stderr.write("no balance crossing found\n")
        balance = TCLK
    sys.stderr.write(f"balance td {corner}: {balance*1e9:.6f} ns\n")

    print("corner,offset_ps,final_q,resolution_ns")
    for td, fq, rt in rows:
        off = (td - balance) * 1e12
        print(f"{corner},{off:.2f},{fq:.4f},{rt:.4f}")


if __name__ == "__main__":
    main()
