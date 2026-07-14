#!/usr/bin/env python3
# Fit the metastability constants tau and T0 from the bench CSVs.
#
# Model. resolution_time = tau * ln(1 / offset) + b
# Transform x = ln(1 / |offset|), y = resolution_time. A line in x.
# The slope of the fitted line is tau. The intercept b carries T0.
#
# T0 relation, stated per the task. The standard metastability window form is
# resolution_time = tau * ln(T0 / offset), which expands to
# tau * ln(1/offset) + tau * ln(T0). So the intercept b = tau * ln(T0) and
# T0 = exp(b / tau). This is the same T0 that sits in
# MTBF = exp(t / tau) / (T0 * f_clk * f_data).
#
# R squared is reported per fit. A low value means the points are not linear
# in ln(1/offset), the exponential resolution model does not hold, and the
# numbers must not be trusted. That is a finding, not a constant.
#
# Usage. python3 scripts/fit_tau.py docs/cdc/sweep_tt_94ab4266.csv \
#                                    docs/cdc/sweep_ss_2160e2ac.csv
# Writes one fit plot per corner into docs/cdc/.

import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(path):
    """Return corner name, |offset| in seconds, resolution in seconds."""
    corner, offs, res = None, [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            corner = row["corner"]
            offs.append(abs(float(row["offset_fs"])) * 1e-15)
            res.append(float(row["resolution_ns"]) * 1e-9)
    return corner, np.array(offs), np.array(res)


def fit(path):
    corner, offs, res = load(path)
    x = np.log(1.0 / offs)
    y = res
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    tau = slope
    t0 = float(np.exp(intercept / tau))
    return corner, x, y, tau, intercept, t0, r2


def plot(corner, x, y, tau, intercept, r2, outdir):
    xs = np.linspace(x.min(), x.max(), 100)
    plt.figure(figsize=(7, 5))
    plt.scatter(x, y * 1e9, s=28, label="bench points, both sides of balance")
    plt.plot(xs, (tau * xs + intercept) * 1e9,
             label=f"fit, tau {tau*1e12:.1f} ps, R2 {r2:.4f}")
    plt.xlabel("ln(1 / |offset|)  [offset in seconds]")
    plt.ylabel("resolution time [ns]")
    plt.title(f"dfxtp_2 master node resolution, corner {corner}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    out = os.path.join(outdir, f"fit_{corner}.png")
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    return out


def main():
    outdir = "docs/cdc"
    print(f"{'corner':8s} {'tau_ps':>9s} {'T0_ps':>9s} {'intercept_ns':>13s} {'R2':>8s} {'N':>3s}")
    for path in sys.argv[1:]:
        corner, x, y, tau, b, t0, r2 = fit(path)
        out = plot(corner, x, y, tau, b, r2, outdir)
        print(f"{corner:8s} {tau*1e12:>9.2f} {t0*1e12:>9.2f} {b*1e9:>13.4f} {r2:>8.4f} {len(x):>3d}  plot {out}")


if __name__ == "__main__":
    main()
