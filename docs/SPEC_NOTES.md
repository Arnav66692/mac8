# SPEC notes, feature queue

SPEC.md is frozen, the version lives inside the file, currently v0.4. This
file collects changes for a future feature bump, one line each. Nothing
here is in force yet. The strobe low across reset release rule that once
sat in this queue is now a stated interface requirement in the spec, so it
has been removed from here. The v0.2, v0.3, and v0.4 clarifications and
corrections all landed in the spec already.

- Fused LDB_MAC command. Latch operand B and multiply accumulate in one command, saving one cycle per dot product element. This is a real feature change, so it waits for a feature version, not a clarification bump.
