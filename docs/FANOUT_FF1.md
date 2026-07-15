# Fanout report, the synchronizer first flop

The keep attribute is a promise. This report is the fact, from the final
hardened netlist. ff1 Q drives exactly one load, the tool inserted hold
buffer, and nothing else. No logic reads the metastability exposed flop.

Netlist. CI run 29401092054, commit 49f5f29, final
nl/tt_um_arnav_mac8.nl.v, sha256
5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0.

## The complete ff1 net connectivity

Every occurrence of the ff1 net in the netlist, grep u_sync.ff1, three
lines total.

| Line | Occurrence | Role |
|---|---|---|
| wire \u_sync.ff1 | declaration | the net |
| _1624_ dfxtp_2 .Q(\u_sync.ff1) | driver | ff1 itself, the only driver |
| hold84 dlygate4sd3_1 .A(\u_sync.ff1) | load | the hold buffer, the only load |

## The path onward to ff2

hold84 .X drives net84. net84 has exactly one load, _1563_ and2_2 .B, the
synchronous reset gate, whose output _0053_ is _1625_ ff2 .D. So the full
ff1 to ff2 path is ff1 Q, hold buffer, reset AND, ff2 D, two cells, both
sanctioned in the round 1.5 keep ruling. The hold buffer is hold fixing,
allowed. The reset AND is the synchronous reset, by design.

## The five protected flops

| Flop | Instance | Cell | Q net loads |
|---|---|---|---|
| u_sync.ff1 | _1624_ | dfxtp_2 | 1, hold84 only |
| u_sync.ff2 | _1625_ | dfxtp_2 | edge detect and arm logic, by design |
| u_sync.ff3 | _1626_ | dfxtp_2 | edge detect, by design |
| u_rst_sync.rst_ff1 | _1636_ | dfxtp_2 | 1, hold buffer hold82, then rst_ff2 D direct |
| u_rst_sync.rst_ff2 | _1635_ | dfxtp_2 | the internal reset tree, by design |

One driver each, five distinct dfxtp_2 instances, no merge, no
replication. Only ff1 and rst_ff1 are metastability exposed, and neither
feeds logic.

## Reproduce

```
grep -n "u_sync.ff1" tt_um_arnav_mac8.nl.v
grep -n "net84" tt_um_arnav_mac8.nl.v
grep -n "u_rst_sync.rst_ff1" tt_um_arnav_mac8.nl.v
```

Three greps against the netlist above. The counts in this report are the
complete output, nothing omitted.
