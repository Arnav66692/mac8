---
tags: [chip-track, signoff]
project: P1
status: manifest, every hash recomputed from a fresh artifact download 2026-08-08
---

# Provenance manifest

One page connecting every artifact hash the package cites to the run that
produced it. All hashes below were recomputed on 2026-08-08 from a fresh
download of the run artifacts, not copied from older documents.

## The sealed run

| Field | Value |
|---|---|
| Repository | github.com/Arnav66692/mac8 |
| Commit | 49f5f298692f274c6613cdc940e0cee991281943 |
| Workflow run | 29401092054, workflow gds, completed 2026-07-15, all jobs green |
| GDS and precheck actions | TinyTapeout/tt-gds-action at ref ttsky26c, resolved to 30d38a7dfc6fda561d452b196fc822af0332ec23 when recorded 2026-07-16 |
| Tiny Tapeout tools | main d65690ee, from the run's commit_id.json |
| Flow | LibreLane 3.0.3 |
| PDK | sky130A, open_pdks 8afc8346a57fe1ab7934ba5a6056ea8b43078e71, from the run's pdk.json |

## Netlists, the raw to powered relationship

The flow emits the same placed and routed design twice. The raw netlist,
nl.v, has no power pins and is what OpenSTA times, the seal hash every
package table cites. The powered netlist, pnl.v, is the same design with
VPWR and VGND ports and per instance power connections added by the flow,
and is what the submission package ships as tt_um_arnav_mac8.v and what
the gate level tests simulate as test/gate_level_netlist.v. Verified this
session, both files carry the identical set of 2989 standard cell
instances, same cell types, same instance names, and only the powered
file contains power pins. The two hashes below are one design, one
transformation apart.

| Artifact | sha256 |
|---|---|
| Raw netlist, final/nl/tt_um_arnav_mac8.nl.v, the seal hash | 5d41493182cd1ece30f2f4a2bdabdf5433400f7b508858161ea6f72db4f13fb0 |
| Powered netlist, final/pnl/tt_um_arnav_mac8.pnl.v, ships as tt_submission tt_um_arnav_mac8.v, local copy test/gate_level_netlist.v | 5c51d76c4ff2103fbcc8aa777b3421a104c778aa878cd2523203c0b89eac2d64 |

## GDS

| Artifact | sha256 |
|---|---|
| tt_submission/tt_um_arnav_mac8.gds, also final/gds, also the render copy | 5f1bae23645628acda6ac34e048324c5ed57117523c580e1ca41f20c616e8884 |

## SDF, all nine corners, from final/sdf of the run

The max_ss_100C_1v60 file is the input of the annotated gate level run,
docs/GL_TIMING.md, local copy test/sdf_max_ss.sdf, byte identical.

| Corner | sha256 |
|---|---|
| max_ss_100C_1v60 | ccb9d44ed7f7b6cde50159603d4cfcd32a464189ee07f9f32ee28adc58f54df5 |
| max_tt_025C_1v80 | f37a42c810bbac91035ca5f56a5bfba64a20a7dcb0820d53f92aa6ffab4f9f85 |
| max_ff_n40C_1v95 | f183cafc741a23d352d9413a45b73c16eb20ec5821f1862cf572098fe4322011 |
| nom_ss_100C_1v60 | 574af6f0cca1b193ec43fbf7e30f469f6b21c69bbbb951466670ba38f3ac6006 |
| nom_tt_025C_1v80 | 72e1cac20e3f9d21157e38baea5ba6142a850444aadc22c6358201ba86badc5e |
| nom_ff_n40C_1v95 | b80d7043d901ad21e5a4b29903d0d30d74c5e25254778cc20d74e441eb28867d |
| min_ss_100C_1v60 | f256c1e3a4ac0d4593d6335053c96c9ec0f062640f604f0bf6b49131b0a86654 |
| min_tt_025C_1v80 | 05b7c0ca40ddad969a24a281b4bdfae528c516ae8da94f6724c4f829a77cf25b |
| min_ff_n40C_1v95 | b6bb49596234e9a95ac97b3898d62860c954ee94c82ef7d47dc9b618d27792eb |

## Where the artifacts live

The run's artifacts, tt_submission, GDS_logs, precheck_reports,
gatelevel_test_results, gds_render, are attached to run 29401092054 under
GitHub's artifact retention. Local copies tracked outside CI are
test/gate_level_netlist.v and test/sdf_max_ss.sdf, both gitignored run
artifacts, and the render copy of the GDS with its own record in the
render folder's PROVENANCE.md. The extracted spice cell provenance for
the metastability bench lives in docs/CDC_MTBF.md and docs/cdc/README.md.
