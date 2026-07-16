---
tags: [chip-track, signoff]
project: P1
status: one open waiver, W1, disposition deferred
---

# Signoff waivers

One home for accepted, characterized deviations. A waiver is not a status
message. Each entry carries the magnitude, the corner as the flow names
it, the affected arcs, the downstream slack, the risk with the sign of the
extrapolation error, and the disposition.

## W1, max transition overage on datapath and reset fanout nets

All numbers from the final hardened run, CI run 29401092054, commit
49f5f29, netlist sha256 5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0.

**What.** Input pin transition times beyond the 0.75 ns library
characterization limit on high fanout nets built by the fanout clone pass.
This is one waiver, W1, with two classes of the same finding, the same max
transition mechanism on two net groups. It is not two waivers.

**Class 1, operand and multiplier fanout, the datapath class.**

| Corner, flow name | Violating pins | Nets | Worst slew |
|---|---|---|---|
| max_ss_100C_1v60 | 243 | about 22, worst net52, net65, net20 | 1.2073 ns on net52 |
| nom_ss_100C_1v60 | 221 | same class | 1.1818 ns at _0818_/A |
| min_ss_100C_1v60 | 180 | same class | 1.1658 ns at _0818_/A |
| max_tt_025C_1v80 | 33 | 3, net52, net65, net20 | 0.7577 ns, 8 ps over |
| all ff corners, nom tt, min tt | 0 | none | clean |

The three named nets carry u_dp.b_q[2] behind fanout52, u_dp.a_q[2]
behind fanout65, and the multiplier internal net _0082_ behind the
fanout20 chain. Affected arcs, the input pins of multiplier array gates
fed by these nets, 11 pins per net.

**Class 2, the synchronized reset tree, found in round three.**

| Corner, flow name | Violating pins | Net | Worst slew |
|---|---|---|---|
| max_ss_100C_1v60 | 11 | net42, one branch of the rst_ff2 fanout | 0.8989 ns |
| nom_ss_100C_1v60 | 11 | net42 | 0.8598 ns |
| min_ss_100C_1v60 | 11 | net42 | 0.8107 ns |

net42 sinks include _1563_/A, the reset AND on the ff1 to ff2 path. The
net is static during operation, it transitions once per reset event, so
the exposure is per reset, not per cycle. The reset release timing paths
from rst_ff2 are met at every corner, and the side input slew does not
enter the B to X arc delay that the MTBF slack uses.

**Downstream slack.** The design's worst setup path at max_ss_100C_1v60
runs through net20, one of the waived nets, and reads plus 1.5557 ns,
run 29401092054 max.rpt, path _1595_ to _1622_. Every path through every
waived net therefore has at least that slack. Max cap is clean, zero
violations at all nine corners, the waived nets included.

**Risk and sign.** The overage means delay lookup beyond the
characterized slew axis, an extrapolation. Treat the error as adverse,
added delay. Paths compose, so the honest charge is not the worst single
pin but the sum of the excesses along one path. The worst setup path at
max_ss_100C_1v60, _1595_ to _1622_, traverses six waived nets in series,
net51 net50 net22 net21 net20 net14, with slew excesses over the 0.75 ns
limit of 0.114, 0.001, 0.342, 0.190, 0.452, and 0.002 ns, summing to about
1.10 ns. Charge every one of those in full as added delay and the path
still holds plus 0.46 ns, 1.41x inside its 1.5557 ns slack. That full sum
is an upper bound twice over, the slack already prices the actual slews on
delay and this charge counts only the extrapolation error, which is a
fraction of the slew excess, not the whole of it. The worst single pin
alone is 0.457 ns, 3.40x inside. Either accounting clears. Hold uses the
same tables and holds 1.75 ns of slack on the sync path at the same
corner.

**Precheck.** The Tiny Tapeout precheck runs 15 checks, all geometry,
connectivity, and naming. It does not gate on max transition. Verified on
the final run, all 15 green.

**Priced fix.** Branch rsz-corners, commit 3cbf169, run 29404662777,
extends the resizer repair corners. It clears nom tt, improves setup
everywhere, holds hold and fit, and reduces but does not clear the ss
counts, 254 to 214, because the flow has no post route repair pass. The
reset tree improves 0.899 to 0.892, same class. A full clear needs post
route repair or a stronger fanout drive strategy.

**Disposition. Deferred, Arnav's call.** Adopting the branch re baselines
the one hash package for a partial improvement on a wart that gates
nothing. The waiver stands on the slack numbers above either way.
