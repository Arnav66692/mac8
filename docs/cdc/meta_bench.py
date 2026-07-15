#!/usr/bin/env python3
# Metastability bench, refined per review round 1.5 item 4.
# Probes the master latch storage node a_466_413# of dfxtp_2, not Q. Q sits
# behind the slave tgate, an inverter, and the output buffer, which
# regenerate and hide the metastable dwell. The master cross coupled pair is
# a_466_413# and a_634_159#, input tgate writes a_466_413# on CLK low, the
# clocked feedback holds it on CLK high, so post edge dwell lives there.
#
# Structure per Beer and Ginosar, single session per grid, models parse once.
# Grid refinement locates the balance, then log spaced fs offsets both sides
# measure the resolution time, the time for the master node to exit the mid
# rail band after the clock edge.
#
# Sweep data generation only. No tau fit, no T0, no MTBF text.

import hashlib
import os
import subprocess
import sys
import tempfile

PDK_ROOT = os.environ.get("PDK_ROOT", os.path.expanduser("~/.volare"))
LIB = os.path.join(PDK_ROOT, "sky130A", "libs.tech", "ngspice", "sky130.lib.spice")
CELL = os.environ["CELL_SPICE"]
NGSPICE = os.environ.get("NGSPICE", "/opt/homebrew/bin/ngspice")
SUBCKT = "sky130_fd_sc_hd__dfxtp_2"
MNODE = "xdut.a_466_413#"   # master latch storage node

CORNERS = {"tt": (1.80, 25, "tt"), "ss": (1.60, 100, "ss")}
TCLK = 5.0e-9
TSTOP = 13.0e-9
TSTEP = 0.2e-12

# Round two overrides, env vars, defaults reproduce the original decks
# exactly. EDGE_CLK and EDGE_D are PWL rise times in seconds, the original
# bench used 20 ps convenience edges on both. RELTOL, TRAN_TMAX, METHOD are
# the solver check knobs. The deck text carries every value, so the deck
# hash changes whenever any override changes, provenance holds.
TMAX = float(os.environ.get("TRAN_TMAX", "0.5e-12"))
EDGE_CLK = float(os.environ.get("EDGE_CLK", "20e-12"))
EDGE_D = float(os.environ.get("EDGE_D", "20e-12"))
RELTOL = os.environ.get("RELTOL", "1e-6")
METHOD = os.environ.get("METHOD", "gear")


def build_deck(corner, td_list, outdir):
    vdd, temp, section = CORNERS[corner]
    lines = [
        f"* metastability refine {SUBCKT} {corner}, master node probe",
        f'.include "{CELL}"',
        f'.lib "{LIB}" {section}',
        "",
        ".param td=5n",
        f"Vpwr VPWR 0 {vdd}",
        "Vgnd VGND 0 0",
        f"Vpb  VPB  0 {vdd}",
        "Vnb  VNB  0 0",
        f"Vclk CLK 0 PWL(0 0 {TCLK:.6e} 0 {TCLK+EDGE_CLK:.6e} {vdd})",
        "Vd   D 0 PWL(0 0 {td} 0 {td+" + f"{EDGE_D*1e12:g}p" + "} " + f"{vdd})",
        f"Xdut CLK D VGND VNB VPB VPWR Q {SUBCKT}",
        "Cload Q 0 5f",
        f".options temp={temp} reltol={RELTOL} abstol=1e-15 vntol=1e-9 method={METHOD}",
        ".control",
    ]
    for i, td in enumerate(td_list):
        out = os.path.join(outdir, f"p_{i:04d}.txt")
        lines += [
            f"alterparam td={td:.9e}",
            "reset",
            f"tran {TSTEP:.2e} {TSTOP:.2e} 0 {TMAX:.2e} uic",
            f"wrdata {out} v({MNODE}) v(q)",
        ]
    lines += [".endc", ".end", ""]
    return "\n".join(lines)


def run_grid(corner, td_list):
    outdir = tempfile.mkdtemp(prefix="metaref_")
    deck = build_deck(corner, td_list, outdir)
    deckpath = os.path.join(outdir, "grid.sp")
    open(deckpath, "w").write(deck)
    r = subprocess.run([NGSPICE, "-b", deckpath], capture_output=True, text=True,
                       timeout=3600)
    results = []
    for i, td in enumerate(td_list):
        path = os.path.join(outdir, f"p_{i:04d}.txt")
        pts = []
        if os.path.exists(path):
            for line in open(path):
                p = line.split()
                if len(p) >= 4:
                    try:
                        pts.append((float(p[0]), float(p[1]), float(p[3])))
                    except ValueError:
                        pass
        results.append((td, pts))
    convergence_note = ""
    if any(not pts for _, pts in results):
        missing = sum(1 for _, pts in results if not pts)
        convergence_note = f"{missing} of {len(td_list)} points produced no data"
        tail = "\n".join(r.stderr.splitlines()[-6:])
        sys.stderr.write(f"CONVERGENCE ISSUE: {convergence_note}\n{tail}\n")
    return results, deck, convergence_note


def final_q(pts, vdd):
    return pts[-1][2] / vdd if pts else None


def resolution_ns(pts, vdd):
    """Last time the master node sits inside the mid rail band after the
    clock edge, relative to the edge. 0.3 to 0.7 of vdd is the band."""
    hi, lo = 0.7 * vdd, 0.3 * vdd
    last = TCLK
    for t, m, _ in pts:
        if t >= TCLK and lo <= m <= hi:
            last = t
    return (last - TCLK) * 1e9


def find_balance(corner, center, span, step):
    vdd = CORNERS[corner][0]
    tds = [center + k * step for k in range(-int(span / step), int(span / step) + 1)]
    results, _, _ = run_grid(corner, tds)
    prev = None
    for td, pts in results:
        fq = final_q(pts, vdd)
        if fq is None:
            continue
        if prev is not None and (prev[1] - 0.5) * (fq - 0.5) < 0:
            frac = (0.5 - prev[1]) / (fq - prev[1])
            return prev[0] + frac * (td - prev[0])
        prev = (td, fq)
    raise RuntimeError(f"no balance crossing in grid at {corner}")


def main():
    corner = sys.argv[1] if len(sys.argv) > 1 else "tt"
    vdd = CORNERS[corner][0]

    b1 = find_balance(corner, TCLK - 20e-12, 60e-12, 2e-12)
    sys.stderr.write(f"L1 balance {corner}: {b1*1e9:.6f} ns\n")
    b2 = find_balance(corner, b1, 3e-12, 100e-15)
    sys.stderr.write(f"L2 balance {corner}: {b2*1e9:.7f} ns\n")
    b3 = find_balance(corner, b2, 150e-15, 4e-15)
    sys.stderr.write(f"L3 balance {corner}: {b3*1e9:.8f} ns\n")
    b4 = find_balance(corner, b3, 6e-15, 0.25e-15)
    sys.stderr.write(f"L4 balance {corner}: {b4*1e9:.9f} ns\n")

    offs = [1e-15, 2e-15, 5e-15, 10e-15, 20e-15, 50e-15,
            100e-15, 200e-15, 500e-15, 1000e-15]
    td_list = [b4 - o for o in reversed(offs)] + [b4 + o for o in offs]
    results, deck, note = run_grid(corner, td_list)
    deckhash = hashlib.sha256(deck.encode()).hexdigest()[:8]

    outname = f"sweep_{corner}_{deckhash}.csv"
    with open(outname, "w") as f:
        f.write("corner,offset_fs,final_q,resolution_ns\n")
        for td, pts in results:
            if not pts:
                continue
            off = (td - b4) * 1e15
            fq = final_q(pts, vdd)
            rt = resolution_ns(pts, vdd)
            f.write(f"{corner},{off:+.2f},{fq:.4f},{rt:.4f}\n")
    sys.stderr.write(f"wrote {outname}, balance {b4*1e9:.9f} ns\n")
    if note:
        sys.stderr.write(f"note: {note}\n")
    print(outname)


if __name__ == "__main__":
    main()
