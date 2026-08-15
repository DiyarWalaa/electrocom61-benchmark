"""
figure_near_duplicate.py -- publication figure of the tightest cross-split pair

Renders IMG_20240220_115315 (test) and IMG_20240220_115316 (train) side by side
with their YOLO boxes drawn and named, and captions each panel with filename,
capture time, split, and the per-box centre shift in pixels.

WHY THIS PAIR

    Three splits, three fates for the same two photographs:

      published                both in TRAIN
      image-level allocator    left panel moved to TEST -- a test<->train
                               near-duplicate at aligned distance 0.00712,
                               the tightest the split created, and the pair
                               with the smallest cross-split time gap at one
                               second (two observations, one pair of photos)
      burst-aware tau=15       both in TRAIN again -- the burst moves whole

    So this figure no longer shows a defect in the released split. It shows the
    defect the released split AVOIDS, which is why it is worth printing: the
    reader can see what "moving whole bursts instead of images" actually buys,
    on a concrete pair rather than in a contamination table.

    The split shown under each panel is read from the built tree, not asserted
    here, so if the released split ever changes this figure changes with it.

RESOLUTION, HONESTLY
    The source images are 640x640 because Roboflow stretch-resized every image
    in the v2 export. Rendering larger cannot add detail that is not there. The
    figure is therefore composed at %d dpi so that the OVERLAYS and TEXT are
    publication-crisp, while the photographs are drawn at their native pixel
    count with nearest-neighbour interpolation -- smoothing would invent
    gradients the sensor never recorded.

COLOUR
    Categorical hues are taken in fixed slot order from the project's reference
    palette rather than chosen ad hoc. Identity is NOT carried by colour: every
    box is directly labelled with its class name, which is what makes the figure
    legible in greyscale, in print, and to a colourblind reader. Each coloured
    rectangle is drawn over a darker underlay stroke because the backdrop is a
    photograph, not a flat surface, and a thin hue alone can vanish against it.

Run with no arguments:

    python scripts/figure_near_duplicate.py

Writes figures/near_duplicate_pair.png and a provenance record under
runs/<YYYYMMDD>_figure_near_duplicate/.
"""

import ast
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")  # no display on this machine; write straight to file
# Embed TrueType rather than Type 3 in the PDF. IEEE rejects Type 3, and
# make_figures.py sets the same two keys for every other figure in the paper.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.patheffects import withStroke  # noqa: E402
from PIL import Image  # noqa: E402


# The two images, and the split each belongs to under the CORRECTED assignment.
STEM_A = "IMG_20240220_115315"
STEM_B = "IMG_20240220_115316"

# Read from the built corrected tree so the split shown in each caption is the
# directory the file actually sits in, rather than a label asserted by hand.
DATASET = os.path.join(ec61.DATA_DIR, "ElectroCom-61_corrected")

OUT_DIR = os.path.join(ec61.REPO_ROOT, "figures")
OUT_PNG = os.path.join(OUT_DIR, "near_duplicate_pair.png")
# PDF alongside the PNG, for the same reason every other figure has one: the
# paper includes vector art so the figure does not resample when the venue
# template changes its column width. pdf.fonttype 42 embeds TrueType rather
# than Type 3, which IEEE requires.
OUT_PDF = os.path.join(OUT_DIR, "near_duplicate_pair.pdf")

DPI = 300

# Rendered size. This is a WIDE figure -- two 640 px panels side by side plus a
# shift table -- so it is a full-text-width exhibit, not a column figure. 7.0 in
# is chosen to match the text width of a two-column IEEE page (about 7.16 in),
# so the figure is included at roughly 1:1 there and its point sizes below are
# the sizes the reader actually sees.
#
# It was previously rendered at 11.0 x 7.4 in with a 6.9 pt shift table, which
# scaled to 2.2 pt in a 3.5 in column and 3.9 pt at this class's text width --
# illegible either way. That could not be fixed by changing the
# \includegraphics width, only by re-rendering, which is what this is.
FIG_W_IN = 7.0
FIG_H_IN = 6.45

# Every point size below is chosen FOR FIG_W_IN, not scaled from a previous
# render. The smallest text in the figure is the per-box shift table; it is the
# one that decides whether the figure survives being placed on a page, so it
# sets the floor and everything else is sized around it.
FS_TITLE     = 10.5   # suptitle
FS_SUBTITLE  = 8.0    # the two explanatory lines under the title
FS_HEADER    = 8.2    # per-panel filename / capture time / split
FS_TABLE     = 8.0    # per-box shift table -- THE FLOOR, do not go below 8
FS_FOOTNOTE  = 8.0    # the two closing lines
FS_BOXLABEL  = 8.0    # class names drawn on the photographs

# Categorical slots 1-5 of the reference palette, in fixed order. Not cycled,
# not reordered, not invented.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

# Ink colours, kept as text tokens rather than series colours.
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
SURFACE = "#fcfcfb"


def read_class_names(data_yaml):
    with open(data_yaml, "r", encoding="utf-8") as fh:
        text = fh.read()
    names = ast.literal_eval(
        re.search(r"^names:\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL).group(1))
    return names


def find_image(stem):
    """Locate an image by capture stem in the corrected tree.

    Returns (split, image_path, label_path). Raises if not found, because a
    figure built from the wrong file is worse than no figure.
    """
    for split in ec61.SPLITS:
        img_dir = os.path.join(DATASET, split, "images")
        if not os.path.isdir(img_dir):
            continue
        for fname in sorted(os.listdir(img_dir)):
            if ec61.parse_stem(fname) == stem:
                base = fname.rsplit(".", 1)[0]
                return (split,
                        os.path.join(img_dir, fname),
                        os.path.join(DATASET, split, "labels", base + ".txt"))
    raise IOError("image with stem %s not found under %s" % (stem, DATASET))


def capture_time(stem):
    """Human-readable capture timestamp recovered from the filename."""
    family, m = ec61.classify_stem(stem)
    if family not in ec61.TIMESTAMPED_FAMILIES:
        return "no timestamp encoded"
    d, t = m.group("date"), m.group("time")
    return "%s-%s-%s %s:%s:%s" % (d[:4], d[4:6], d[6:8], t[:2], t[2:4], t[4:6])


def _overlap(a, b):
    """Do two (x0, y0, x1, y1) rectangles intersect?"""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def panel_width_pt():
    """Printed width of one image panel, in points.

    Derived from the gridspec below: the axes area spans left=0.035 to
    right=0.965 of the figure, split into two columns with wspace=0.05 of the
    column width between them. Kept as a function so the layout constants have
    one home rather than two.
    """
    usable = (0.965 - 0.035) * FIG_W_IN
    return (usable / (2.0 + 0.05)) * 72.27


def draw_panel(ax, img_path, boxes, names, colors, size):
    """Draw one image with its boxes and class labels.

    Labels are placed with simple collision avoidance. Four candidate positions
    are tried per box, in order, and the first that does not overlap an
    already-placed label wins. Without this, neighbouring boxes (here Fuse and
    Diode, whose top edges are ~10 px apart) print their labels on top of each
    other and the figure becomes unreadable at print size.
    """
    img = Image.open(img_path)
    # Nearest-neighbour: the source is 640x640 and already stretched once by
    # Roboflow. Interpolating again would fabricate detail.
    ax.imshow(img, interpolation="nearest")
    ax.set_xlim(0, size)
    ax.set_ylim(size, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor(INK_SECONDARY)
        spine.set_linewidth(0.8)

    # Approximate text metrics in DATA units (image pixels). A panel spans
    # `size` data units across its own printed width, so the conversion has to
    # be DERIVED from the figure width -- hardcoding it (it was 346 pt, for an
    # 11 in figure) silently breaks the collision avoidance the moment the
    # figure is resized, which is exactly what a resize is for.
    fs = FS_BOXLABEL
    pt_to_data = size / panel_width_pt()
    char_w = fs * 0.60 * pt_to_data
    line_h = fs * 1.45 * pt_to_data
    pad = 3.0 * pt_to_data

    placed = []
    for (cid, cx, cy, w, h), color in zip(boxes, colors):
        x = (cx - w / 2.0) * size
        y = (cy - h / 2.0) * size
        bw, bh = w * size, h * size
        # Dark underlay first, then the hue on top: the backdrop is a
        # photograph, so a thin coloured line alone can disappear into it.
        ax.add_patch(Rectangle((x, y), bw, bh, fill=False,
                               edgecolor="#000000", linewidth=4.0, alpha=0.55))
        ax.add_patch(Rectangle((x, y), bw, bh, fill=False,
                               edgecolor=color, linewidth=2.0))

        label = names[cid]
        tw = len(label) * char_w + 2 * pad
        th = line_h
        # Above-left, then inside-top-left, then above-right, then inside-bottom.
        candidates = [
            (x, y - th - 2.0),
            (x + 3.0, y + 3.0),
            (x + bw - tw, y - th - 2.0),
            (x + 3.0, y + bh - th - 3.0),
        ]
        rect = None
        for cx0, cy0 in candidates:
            cx0 = max(0.0, min(cx0, size - tw))   # keep inside the panel
            cy0 = max(0.0, min(cy0, size - th))
            cand = (cx0, cy0, cx0 + tw, cy0 + th)
            if not any(_overlap(cand, p) for p in placed):
                rect = cand
                break
        if rect is None:                          # every option collided
            rect = (max(0.0, min(candidates[0][0], size - tw)),
                    max(0.0, min(candidates[0][1], size - th)))
            rect = (rect[0], rect[1], rect[0] + tw, rect[1] + th)
        placed.append(rect)

        # Direct label. Identity must not depend on hue.
        ax.text(rect[0] + pad, (rect[1] + rect[3]) / 2.0, label,
                fontsize=fs, color="#ffffff", va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.22", facecolor=color,
                          edgecolor="none", alpha=0.95),
                path_effects=[withStroke(linewidth=1.6, foreground="#000000")])


def main():
    # Was a hand-rolled check with its own wording. Routed through ec61 on
    # 2026-08-15 so the corrected tree has one message, not three.
    rc = ec61.require_inputs("corrected")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("figure_near_duplicate")
    names = read_class_names(os.path.join(DATASET, "data.yaml"))

    split_a, img_a, lbl_a = find_image(STEM_A)
    split_b, img_b, lbl_b = find_image(STEM_B)

    with Image.open(img_a) as im:
        size_a = im.size
    with Image.open(img_b) as im:
        size_b = im.size
    if size_a != size_b:
        sys.stderr.write("images differ in size: %s vs %s\n" % (size_a, size_b))
        return 1
    size = size_a[0]

    boxes_a = sorted(ec61.load_boxes(lbl_a))
    boxes_b = sorted(ec61.load_boxes(lbl_b))

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"stems": [STEM_A, STEM_B], "dpi": DPI, "palette": PALETTE,
                "image_size_px": size, "dataset": DATASET,
                "interpolation": "nearest (source already stretch-resized once)"},
        extra={"output": OUT_PNG, "output_pdf": OUT_PDF,
               "pair_identified_by": "runs/20260804_duplicate_contamination"},
    )

    # The two images must carry the same class inventory for a per-box shift to
    # be defined at all. Checked, not assumed.
    inv_a = sorted(c for c, _, _, _, _ in boxes_a)
    inv_b = sorted(c for c, _, _, _, _ in boxes_b)
    if inv_a != inv_b:
        sys.stderr.write("class inventories differ; per-box shift undefined\n")
        return 1

    # Per-box centre shift in pixels. Classes are unique within each image here
    # (one instance each), so matching by class id is unambiguous.
    shifts = []
    b_by_cid = {c: (cx, cy, w, h) for c, cx, cy, w, h in boxes_b}
    for (cid, cx, cy, w, h) in boxes_a:
        bx, by, _bw, _bh = b_by_cid[cid]
        dx = (bx - cx) * size
        dy = (by - cy) * size
        shifts.append((cid, names[cid], dx, dy, math.hypot(dx, dy)))

    ec61.write_csv(
        os.path.join(run_dir, "per_box_centre_shift.csv"),
        ["class_id", "class_name", "dx_px", "dy_px", "distance_px"],
        [[c, n, "%.2f" % dx, "%.2f" % dy, "%.2f" % d] for (c, n, dx, dy, d) in shifts],
    )

    colors = [PALETTE[i % len(PALETTE)] for i in range(len(boxes_a))]

    # ---- compose -------------------------------------------------------
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), dpi=DPI, facecolor=SURFACE)
    # height_ratios gives the caption block a larger share than it had at 11 in:
    # at 8 pt the header and the shift table need more vertical room than they
    # did at 6.9, and a text block that overflows its cell does not shrink, it
    # draws over its neighbour.
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.46],
                          hspace=0.05, wspace=0.05,
                          left=0.035, right=0.965, top=0.866, bottom=0.100)

    fig.suptitle("The near-duplicate pair the released split keeps together",
                 fontsize=FS_TITLE, color=INK, y=0.982, fontweight="bold")
    # Wrapped explicitly, and every line below was measured against FIG_W_IN.
    # matplotlib does not wrap figure text: an over-long line runs off both
    # edges rather than folding, so the break points are chosen here.
    fig.text(0.5, 0.936,
             "Shot one second apart, five identical components. "
             "Under the published split both sit in train.",
             ha="center", fontsize=FS_SUBTITLE, color=INK_SECONDARY)
    fig.text(0.5, 0.915,
             "An image-level allocator moved the left panel to test, "
             "creating a test↔train near-duplicate.",
             ha="center", fontsize=FS_SUBTITLE, color=INK_SECONDARY)
    fig.text(0.5, 0.894,
             "The released burst-aware split (τ=15 s) moves whole bursts, "
             "so both stay in train.",
             ha="center", fontsize=FS_SUBTITLE, color=INK_SECONDARY)

    def shift_lines(sign):
        """Per-box shift text FROM this panel TO the other one.

        `shifts` is measured A -> B, so the right-hand panel must negate it.
        Printing the same signs under both panels would state that each image
        is displaced in the same direction from the other, which is impossible.
        """
        head = "  %-15s %6s %6s %8s" % ("", "dx", "dy", "|shift|")
        body = "\n".join(
            "  %-15s %+6.1f %+6.1f %6.1f px" % (n[:15], sign * dx, sign * dy, d)
            for (_c, n, dx, dy, d) in shifts)
        return head + "\n" + body

    for col, (stem, img_path, boxes, split, sign, other) in enumerate([
            (STEM_A, img_a, boxes_a, split_a, +1.0, STEM_B),
            (STEM_B, img_b, boxes_b, split_b, -1.0, STEM_A)]):
        ax = fig.add_subplot(gs[0, col])
        draw_panel(ax, img_path, boxes, names, colors, size)

        cap = fig.add_subplot(gs[1, col])
        cap.axis("off")
        header = ("%s.jpg\ncaptured %s\nsplit: %s   |   %d×%d px"
                  % (stem, capture_time(stem), split.upper(), size, size))
        cap.text(0.0, 1.0, header, va="top", ha="left", fontsize=FS_HEADER,
                 color=INK, family="monospace", linespacing=1.5)
        cap.text(0.0, 0.62,
                 "per-box centre shift, this panel → %s:\n%s"
                 % (other[-6:], shift_lines(sign)),
                 va="top", ha="left", fontsize=FS_TABLE, color=INK_SECONDARY,
                 family="monospace", linespacing=1.45)

    # Two lines, not one: at this figure width a single line of this text
    # runs off both edges. Wrapped explicitly rather than relying on a
    # bounding box, so the break point is chosen rather than arbitrary.
    max_shift = max(d for (_c, _n, _dx, _dy, d) in shifts)
    fig.text(0.5, 0.044,
             "Same five classes in both panels, one instance each. Boxes are "
             "the dataset's own YOLO annotations, unmodified.",
             ha="center", fontsize=FS_FOOTNOTE, color=INK_SECONDARY)
    fig.text(0.5, 0.016,
             "Largest per-box centre shift: %.1f px of %d (%.1f%%)."
             % (max_shift, size, 100.0 * max_shift / size),
             ha="center", fontsize=FS_FOOTNOTE, color=INK_SECONDARY)

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    fig.savefig(OUT_PNG, dpi=DPI, facecolor=SURFACE)
    fig.savefig(OUT_PDF, facecolor=SURFACE)   # vector, no dpi needed
    plt.close(fig)

    out_px = (int(FIG_W_IN * DPI), int(FIG_H_IN * DPI))
    print("wrote %s" % OUT_PNG)
    print("wrote %s (%.1f KB)" % (OUT_PDF, os.path.getsize(OUT_PDF) / 1024.0))
    print("  %d x %d px at %d dpi, %.1f KB"
          % (out_px[0], out_px[1], DPI, os.path.getsize(OUT_PNG) / 1024.0))
    print("  panels: %s (%s) | %s (%s)" % (STEM_A, split_a, STEM_B, split_b))
    print("  provenance: %s" % run_dir)
    for (_c, n, dx, dy, d) in shifts:
        print("    %-30s dx=%+6.2f dy=%+6.2f |d|=%5.2f px" % (n, dx, dy, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
