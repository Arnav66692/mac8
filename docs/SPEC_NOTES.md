# SPEC notes, v0.2 queue

SPEC.md is frozen at v0.1 and stays untouched. This file collects changes for a
future v0.2 bump. One line each. Nothing here is in force yet.

- Driver rule clarification. Hold strobe low across reset release, so the first command after reset needs a fresh rising edge.
- Fused LDB_MAC command. Latch operand B and multiply accumulate in one command, saving one cycle per dot product element.
