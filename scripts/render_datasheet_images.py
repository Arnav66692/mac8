#!/usr/bin/env python3
# Renders the two datasheet images in docs/ from the sealed GDS, offscreen,
# with the sky130A layer colors from the PDK's KLayout properties file.
# Added in the submission readiness audit so the images are reproducible
# from a committed script instead of a one off session. The input is the
# sealed run's GDS, sha256 recorded in docs/PROVENANCE.md, and the caption
# provenance line lives next to the images in docs/info.md.
#
#   usage. python3 scripts/render_datasheet_images.py <gds> [outdir]
#   needs. pip install klayout, and the volare sky130A PDK for the colors.

import sys
from pathlib import Path

import klayout.db as db
import klayout.lay as lay

PDK_LYP = Path.home() / ".volare/sky130A/libs.tech/klayout/tech/sky130A.lyp"
FULL_W, FULL_H = 1400, 1000
ZOOM_W, ZOOM_H = 1200, 800


def make_view(gds: str) -> lay.LayoutView:
    view = lay.LayoutView()
    view.set_config("background-color", "#ffffff")
    view.set_config("grid-visible", "false")
    view.set_config("text-visible", "false")
    view.load_layout(gds, 0)
    if PDK_LYP.is_file():
        view.load_layer_props(str(PDK_LYP))
    view.max_hier_levels = 20
    return view


def main() -> None:
    gds = sys.argv[1] if len(sys.argv) > 1 else "../render/mac8.gds"
    outdir = Path(sys.argv[2] if len(sys.argv) > 2 else "docs")

    layout = db.Layout()
    layout.read(gds)
    top = layout.top_cell()
    bbox = top.dbbox()
    print(f"top cell {top.name}, die {bbox.width():.1f} x {bbox.height():.1f} um")

    view = make_view(gds)
    view.zoom_fit()
    full = outdir / "gds_full_die.png"
    view.save_image(str(full), FULL_W, FULL_H)
    print(f"wrote {full}")

    # Interior window with individual standard cell rows visible, a 30 um
    # wide strip a third of the way up the core.
    x0 = bbox.left + bbox.width() * 0.35
    y0 = bbox.bottom + bbox.height() * 0.33
    view.zoom_box(db.DBox(x0, y0, x0 + 30.0, y0 + 20.0))
    zoom = outdir / "gds_cell_rows.png"
    view.save_image(str(zoom), ZOOM_W, ZOOM_H)
    print(f"wrote {zoom}")


if __name__ == "__main__":
    main()
