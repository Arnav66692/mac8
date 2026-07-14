---
tags: [chip-track, cdc]
project: P1
status: draft, tau and T0 pending sourcing
---

# CDC MTBF

The derivation body is Arnav's, pending his paste. This file holds the STA
traceable inputs meanwhile, per review round 1.5 item 3.

## STA traceable inputs

The ff1 to ff2 synchronizer path, from the hardened netlist STA of CI run
29352875225, commit e82437b, the keep attribute run. Sources, the per corner
stapostpnr reports. Arrival and hold slack from the min.rpt path launched at
_1614_ ending at _1615_. Required time and capture clock from the max.rpt
endpoint block at _1615_. Setup slack is required minus arrival, same corner
directory, one liberty per corner. All values in ns.

| Value | nom_tt_025C_1v80 | max_ss_100C_1v60 |
|---|---|---|
| Launch clock arrival at ff1 CLK | 0.442575 | 0.774971 |
| Data path delay, ff1 CLK to ff2 D | 1.007156 | 2.014390 |
| Data arrival at ff2 D | 1.449731 | 2.789361 |
| Capture clock arrival at ff2 CLK | 20.439569 | 20.769043 |
| Clock uncertainty | 0.250000 | 0.250000 |
| Library setup time, dfxtp_2 | 0.107851 | 0.271807 |
| Setup required time | 20.081718 | 20.247238 |
| Setup slack, ff1 to ff2 | 18.631987 | 17.457877 |
| Hold slack, ff1 to ff2 | 0.788806 | 1.839709 |

Path cells in order, _1614_ dfxtp_2 Q, hold90 dlygate4sd3_1, _1553_ and2_2,
_1615_ dfxtp_2 D. The delay buffer and the reset AND are inside the data path
delay row.
