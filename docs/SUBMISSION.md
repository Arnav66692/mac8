# Submission package and candidate choice

The repository's `info.yaml` selects the baseline `tt_um_arnav_mac8` and
spec v0.5. Its fresh build is
[37242546187](https://github.com/Arnav66692/mac8/actions/runs/37242546187).
The raw netlist matches the historical sealed netlist. W1 remains its
documented max-transition waiver.

The fused design is a separate experiment. Its build is
[37242546160](https://github.com/Arnav66692/mac8/actions/runs/37242546160),
top `tt_um_arnav_mac8_fused`, protocol in
[experiments/fused/SPEC.md](../experiments/fused/SPEC.md).
Both builds use source commit `9ac84c5eb349cf04ce8d133a79f4d48aa719bc58`.
Its opcode 000 executes LDB_MAC, so baseline software using NOP is not
compatible. Candidate transition exceptions require their own review.

Before changing the submission candidate, complete that review and use
the current shuttle's official template and flow. Stage the candidate's
top, source list and datasheet together, as the experiment workflow does,
then rerun the full checks. The experiment workflow uses the historical
ttsky26c flow for a controlled comparison. That passing result alone does
not establish compatibility with a different shuttle.

For the [Tiny Tapeout creation portal](https://app.tinytapeout.com/projects/create),
the concrete baseline package is the public
[MAC8 repository](https://github.com/Arnav66692/mac8), its selected top and
frozen spec, the build link above, archived metrics and prechecks, and
[bring-up guide](BRINGUP.md). Check the current
[HDL template](https://tinytapeout.com/hdl/templates/) when selecting a
shuttle. An authenticated portal session and a candidate decision are
needed to create or revise a project.

The saved project history does not establish the portal project ID,
revision, selected commit, submission timestamp, payment or allocation.
Record those from the actual portal and receipt in the private vault.
No portal project or purchase was created by this implementation work.

For your resume now, use the implemented design, bit-exact application,
measured simulation cycles and routed comparison. Add submitted,
fabricated or silicon-validated when the corresponding evidence exists.
