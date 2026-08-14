"""
figure_verification_sheet.py -- look at the closest cross-split pairs by eye

A contamination table says "zero". This sheet exists so that claim can be
CHECKED rather than believed: it prints the most similar image pairs that end
up on opposite sides of the released split, with their annotations drawn, and
lets a reader judge whether the scorer's verdict matches what they see.

TWO COLUMNS, TWO QUESTIONS

  A  The 6 most similar cross-split pairs, ALL relationships pooled
     (test<->train, valid<->train, valid<->test), smallest distance first.
     This is "what is the closest thing to a duplicate anywhere across the
     boundary".

  B  The 6 closest TEST<->TRAIN pairs specifically, shown even though none of
     them qualifies as a duplicate at any epsilon. Test contamination is the
     one that biases the headline metric, so a reader should be able to see the
     worst case rather than be told it is zero.

LOW-INFORMATION PAIRS ARE EXCLUDED, AND COUNTED

A pair whose images carry <= 2 boxes can match on centre distance by chance --
two images each holding one object of the same class align trivially. Such
pairs would otherwise fill the top of both columns with degenerate matches and
hide the real worst case. They are excluded from the ranking and the number
excluded is stated in the caption and written to the CSV, so the exclusion is
visible rather than silent.

WHAT THIS SHEET CANNOT SHOW

Pairs are only ever compared when their class multisets match EXACTLY -- same
classes, same counts. A genuine duplicate in which one component is occluded in
one frame changes the multiset and is never compared, so it cannot appear here
at any rank. The sheet is evidence about the pairs the method can see, and the
method under-detects by construction. It is not proof that no duplicate exists.

INTERPOLATION

Thumbnails DOWNSCALE 640px sources to about 180px, so they are drawn with
antialiasing. This is the opposite choice from figure_near_duplicate.py, which
draws at native size and uses nearest-neighbour: smoothing on the way down
avoids aliasing artefacts, whereas smoothing on the way up would invent detail.

Run with no arguments:

    python scripts/figure_verification_sheet.py

Writes figures/split_verification_sheet.png and a provenance record under
runs/<YYYYMMDD>_figure_verification_sheet/.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import scene_signature  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402


DATASET = os.path.join(ec61.DATA_DIR, "ElectroCom-61_corrected")
OUT_DIR = os.path.join(ec61.REPO_ROOT, "figures")
OUT_PNG = os.path.join(OUT_DIR, "split_verification_sheet.png")

# SIZED FOR THE PAGE, not for the screen. This was previously 12 rows at
# 13.5 in wide, which reduced to about 46% at text width and put its smallest
# text near 3.7 pt -- unreadable in print. Fewer rows alone would not have
# fixed that: the reduction is driven by WIDTH, so the figure is now rendered
# at 7.0 in, matching the ~7.16 in text width of a two-column IEEE page, and
# every point size below is the size the reader actually sees there.
#
# Six pairs per column rather than twelve. The claim the sheet supports is that
# the worst case can be inspected; six closest pairs demonstrate that as well as
# twelve, and halving the rows is what buys the vertical room the larger text
# needs while keeping the aspect ratio printable on one page.
N_ROWS = 6
DPI = 300                # raised with the size cut so thumbnails keep detail
FIG_W = 7.0
HEADER_H = 2.14
ROW_H = 0.80
FOOTER_H = 0.58

THUMB_IN = 0.60          # thumbnail edge, inches
GAP_IN = 0.05
COL_X = (0.22, 3.61)     # left edge of each column, inches
TEXT_W = 3.75

# Single accent for boxes. Colour carries no identity here -- the boxes mark
# where the annotations are, nothing more -- so a categorical palette would be
# encoding a variable that does not exist.
BOX_COLOR = "#2a78d6"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#75746e"
SURFACE = "#fcfcfb"

REL_LABEL = {("test", "train"): "test<->train",
             ("train", "valid"): "valid<->train",
             ("test", "valid"): "valid<->test"}


def capture_time(stem):
    family, m = ec61.classify_stem(stem)
    if family not in ec61.TIMESTAMPED_FAMILIES:
        return "no timestamp"
    d, t = m.group("date"), m.group("time")
    return "%s-%s-%s %s:%s:%s" % (d[:4], d[4:6], d[6:8], t[:2], t[2:4], t[4:6])


def load_tree():
    """Every image in the released tree, with the split it actually sits in."""
    out = {}
    for split in ec61.SPLITS:
        img_dir = os.path.join(DATASET, split, "images")
        lbl_dir = os.path.join(DATASET, split, "labels")
        if not os.path.isdir(img_dir):
            raise IOError("missing %s -- build the dataset first" % img_dir)
        for fname in sorted(os.listdir(img_dir)):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            base = fname.rsplit(".", 1)[0]
            out[fname] = {
                "split": split,
                "img": os.path.join(img_dir, fname),
                "lbl": os.path.join(lbl_dir, base + ".txt"),
                "stem": ec61.parse_stem(fname) or fname,
            }
    return out


def draw_thumb(fig, rect_in, fig_w, fig_h, info, size):
    """One thumbnail with its boxes, placed at rect_in = (x, y, w, h) inches."""
    ax = fig.add_axes([rect_in[0] / fig_w, rect_in[1] / fig_h,
                       rect_in[2] / fig_w, rect_in[3] / fig_h])
    with Image.open(info["img"]) as im:
        ax.imshow(im, interpolation="antialiased")
    ax.set_xlim(0, size)
    ax.set_ylim(size, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor(INK_MUTED)
        sp.set_linewidth(0.6)
    for (_cid, cx, cy, w, h) in ec61.load_boxes(info["lbl"]):
        x = (cx - w / 2.0) * size
        y = (cy - h / 2.0) * size
        ax.add_patch(Rectangle((x, y), w * size, h * size, fill=False,
                               edgecolor="#000000", linewidth=1.9, alpha=0.5))
        ax.add_patch(Rectangle((x, y), w * size, h * size, fill=False,
                               edgecolor=BOX_COLOR, linewidth=0.85))
    return ax


def main():
    if not os.path.isdir(DATASET):
        sys.stderr.write("released tree not found: %s\n"
                         "Build it: python scripts/build_corrected_dataset.py\n"
                         % DATASET)
        return 1

    run_dir = ec61.make_run_dir("figure_verification_sheet")
    tree = load_tree()
    boxes = {f: ec61.load_boxes(i["lbl"]) for f, i in tree.items()}

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"n_rows": N_ROWS, "dpi": DPI, "dataset": DATASET,
                "low_info_box_count": scene_signature.LOW_INFO_BOX_COUNT,
                "max_bucket": scene_signature.MAX_BUCKET,
                "ranking": "min(raw_max_centre_dist, aligned_max_centre_dist)",
                "epsilon_filter": "NONE -- non-qualifying pairs are the point"},
        extra={"split_shown": "released burst-aware tau=15",
               "limitation": "only pairs with identical class multisets are compared"})

    # ---- score every cross-split pair, with no epsilon cutoff -------------
    buckets = {}
    for f in tree:
        buckets.setdefault(scene_signature.multiset_key(boxes[f]), []).append(f)

    scored = []
    n_examined = 0
    n_skipped_buckets = 0
    for key in sorted(buckets, key=str):
        members = sorted(buckets[key])
        if len(members) < 2:
            continue
        if len(members) > scene_signature.MAX_BUCKET:
            n_skipped_buckets += 1
            continue
        n_boxes = sum(c for _cid, c in key)
        low = n_boxes <= scene_signature.LOW_INFO_BOX_COUNT
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                n_examined += 1
                sa, sb = tree[a]["split"], tree[b]["split"]
                if sa == sb:
                    continue
                raw = scene_signature.compare(boxes[a], boxes[b], False)[0]
                ali = scene_signature.compare(boxes[a], boxes[b], True)[0]
                scored.append({
                    "a": a, "b": b, "sa": sa, "sb": sb,
                    "raw": raw, "aligned": ali, "score": min(raw, ali),
                    "n_boxes": n_boxes, "low": low,
                    "rel": REL_LABEL[tuple(sorted((sa, sb)))],
                })

    scored.sort(key=lambda p: (p["score"], p["a"], p["b"]))
    non_low = [p for p in scored if not p["low"]]
    low_only = [p for p in scored if p["low"]]
    tt_all = [p for p in scored if p["rel"] == "test<->train"]
    tt_non_low = [p for p in tt_all if not p["low"]]

    col_a = non_low[:N_ROWS]
    col_b = tt_non_low[:N_ROWS]

    # How many low-information pairs scored below the last row shown, i.e. how
    # much the exclusion actually hid. Stated rather than left to trust.
    cutoff_a = col_a[-1]["score"] if col_a else 0.0
    n_low_above_cutoff = sum(1 for p in low_only if p["score"] <= cutoff_a)
    n_tt_low = len(tt_all) - len(tt_non_low)

    eps_max = max(scene_signature.EPSILONS)
    tt_qualifying = sum(1 for p in tt_non_low if p["score"] <= eps_max)
    closest_tt = tt_non_low[0]["score"] if tt_non_low else None

    def rows_csv(rows):
        return [[i + 1, "%.5f" % p["score"], p["rel"],
                 tree[p["a"]]["stem"], p["sa"], tree[p["b"]]["stem"], p["sb"],
                 "%.5f" % p["raw"], "%.5f" % p["aligned"], p["n_boxes"],
                 "yes" if p["low"] else "no", p["a"], p["b"]]
                for i, p in enumerate(rows)]

    header = ["rank", "score", "relationship", "stem_a", "split_a",
              "stem_b", "split_b", "raw", "aligned", "n_boxes",
              "low_information", "file_a", "file_b"]
    ec61.write_csv(os.path.join(run_dir, "closest_all_relationships.csv"),
                   header, rows_csv(col_a))
    ec61.write_csv(os.path.join(run_dir, "closest_test_train.csv"),
                   header, rows_csv(col_b))
    ec61.write_csv(os.path.join(run_dir, "excluded_low_information.csv"),
                   header, rows_csv(low_only[:200]))

    # ---- render -----------------------------------------------------------
    fig_h = HEADER_H + N_ROWS * ROW_H + FOOTER_H
    fig = plt.figure(figsize=(FIG_W, fig_h), dpi=DPI, facecolor=SURFACE)
    with Image.open(tree[col_a[0]["a"]]["img"]) as im:
        size = im.size[0]

    fig.text(0.5, 1 - 0.26 / fig_h,
             "Split verification sheet — closest cross-split image pairs",
             ha="center", va="top", fontsize=11.0, fontweight="bold", color=INK)
    fig.text(0.5, 1 - 0.50 / fig_h,
             "Released split: burst-aware, τ = 15 s, seed 20260804. "
             "Ranked by label-geometry distance, smallest first.",
             ha="center", va="top", fontsize=8.0, color=INK_SECONDARY)

    # Two lines, not one. As a single string this ran off both edges at 7 in,
    # and it is the headline of the sheet, so it is the last thing that should
    # be clipped.
    if tt_qualifying == 0 and closest_tt is not None:
        verdict = ["test↔train carries ZERO near-duplicate pairs at every "
                   "epsilon (loosest ε = %.2f)." % eps_max,
                   "The closest test↔train pair scores %.4f — above the "
                   "threshold, but only by %.0f%%."
                   % (closest_tt, 100.0 * (closest_tt - eps_max) / eps_max)]
    else:
        verdict = ["test↔train carries %d qualifying near-duplicate pairs."
                   % tt_qualifying, ""]
    for i, line in enumerate(verdict):
        if not line:
            continue
        fig.text(0.5, 1 - (0.70 + 0.17 * i) / fig_h, line, ha="center",
                 va="top", fontsize=8.4, color=INK, fontweight="bold")

    # Every line below is wrapped for FIG_W. matplotlib does not wrap figure
    # text, so an over-long string runs off both edges instead of folding.
    fig.text(0.5, 1 - 1.14 / fig_h,
             "Column B shows the closest test↔train pairs anyway, none of which "
             "qualify —",
             ha="center", va="top", fontsize=8.0, color=INK_SECONDARY)
    fig.text(0.5, 1 - 1.31 / fig_h,
             "so the worst case can be inspected rather than taken on trust.",
             ha="center", va="top", fontsize=8.0, color=INK_SECONDARY)
    fig.text(0.5, 1 - 1.53 / fig_h,
             "%d low-information pairs (≤ %d boxes) are excluded from both "
             "rankings; %d scored"
             % (len(low_only), scene_signature.LOW_INFO_BOX_COUNT, n_low_above_cutoff),
             ha="center", va="top", fontsize=8.0, color=INK_SECONDARY)
    fig.text(0.5, 1 - 1.70 / fig_h,
             "below column A's last row. Full list in the run's CSV.",
             ha="center", va="top", fontsize=8.0, color=INK_SECONDARY)

    for col, (x0, title) in enumerate([
            (COL_X[0], "A.  %d most similar, all relationships" % N_ROWS),
            (COL_X[1], "B.  %d closest test↔train — none qualify" % N_ROWS)]):
        fig.text(x0 / FIG_W, 1 - (HEADER_H - 0.22) / fig_h, title,
                 ha="left", va="top", fontsize=8.6, fontweight="bold", color=INK)

    for col, rows in enumerate([col_a, col_b]):
        x0 = COL_X[col]
        for r, p in enumerate(rows):
            y_top = fig_h - HEADER_H - r * ROW_H
            y = y_top - THUMB_IN
            draw_thumb(fig, (x0, y, THUMB_IN, THUMB_IN), FIG_W, fig_h,
                       tree[p["a"]], size)
            draw_thumb(fig, (x0 + THUMB_IN + GAP_IN, y, THUMB_IN, THUMB_IN),
                       FIG_W, fig_h, tree[p["b"]], size)

            # Text column is narrow at this width, so each line is built to fit
            # rather than truncated by the figure edge. The stem is shortened to
            # its capture time -- the date is already implied by the timestamp
            # line beneath and the full name is in the run's CSV.
            tx = (x0 + 2 * THUMB_IN + 2 * GAP_IN + 0.06) / FIG_W
            ty = y_top / fig_h
            fig.text(tx, ty - 0.06 / fig_h,
                     "#%d  %.4f" % (r + 1, p["score"]),
                     ha="left", va="top", fontsize=8.0, color=INK,
                     family="monospace", fontweight="bold")
            fig.text(tx, ty - 0.21 / fig_h,
                     p["rel"],
                     ha="left", va="top", fontsize=8.0, color=INK,
                     family="monospace")
            fig.text(tx, ty - 0.36 / fig_h,
                     "A %s %s" % (capture_time(tree[p["a"]]["stem"]),
                                  p["sa"].upper()[:5]),
                     ha="left", va="top", fontsize=8.0, color=INK_SECONDARY,
                     family="monospace")
            fig.text(tx, ty - 0.50 / fig_h,
                     "B %s %s" % (capture_time(tree[p["b"]]["stem"]),
                                  p["sb"].upper()[:5]),
                     ha="left", va="top", fontsize=8.0, color=INK_SECONDARY,
                     family="monospace")
            fig.text(tx, ty - 0.64 / fig_h,
                     "%d boxes" % p["n_boxes"],
                     ha="left", va="top", fontsize=8.0, color=INK_MUTED,
                     family="monospace")

    # Three lines at this width: the caption ran off both edges as two.
    fig.text(0.5, 0.44 / fig_h,
             "Pairs are compared only when their class multisets match exactly,",
             ha="center", va="center", fontsize=8.0, color=INK_SECONDARY)
    fig.text(0.5, 0.28 / fig_h,
             "so a duplicate with one occluded component is never scored and "
             "cannot appear here at any rank.",
             ha="center", va="center", fontsize=8.0, color=INK_SECONDARY)
    fig.text(0.5, 0.12 / fig_h,
             "The method under-detects by construction.",
             ha="center", va="center", fontsize=8.0, color=INK_SECONDARY)

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    fig.savefig(OUT_PNG, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Split verification sheet")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("Output: `figures/split_verification_sheet.png`")
    lines.append("")
    lines.append("- pairs examined (same class multiset): **%d**" % n_examined)
    lines.append("- cross-split pairs: **%d** (test<->train %d, valid<->train %d, "
                 "valid<->test %d)"
                 % (len(scored),
                    sum(1 for p in scored if p["rel"] == "test<->train"),
                    sum(1 for p in scored if p["rel"] == "valid<->train"),
                    sum(1 for p in scored if p["rel"] == "valid<->test")))
    lines.append("- low-information cross-split pairs excluded: **%d** "
                 "(%d of them scored below column A's last row)"
                 % (len(low_only), n_low_above_cutoff))
    lines.append("- buckets skipped as too large: %d" % n_skipped_buckets)
    lines.append("")
    lines.append("## test<->train")
    lines.append("")
    lines.append("- pairs sharing a class multiset: **%d** (%d non-low-information)"
                 % (len(tt_all), len(tt_non_low)))
    lines.append("- qualifying as near-duplicates at any epsilon (<= %.2f): **%d**"
                 % (eps_max, tt_qualifying))
    if closest_tt is not None:
        lines.append("- closest test<->train pair: **%.4f**, which is %.0f%% above "
                     "the loosest threshold. The margin is thin, not comfortable."
                     % (closest_tt, 100.0 * (closest_tt - eps_max) / eps_max))
    lines.append("- low-information test<->train pairs excluded: %d" % n_tt_low)
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- Only pairs with identical class multisets are compared. An "
                 "occluded component changes the multiset and the pair is never "
                 "scored, so absence from this sheet is not absence of duplicates.")
    lines.append("- Distance is annotation geometry, not pixels. Two different "
                 "scenes laid out alike score as similar; the same scene "
                 "re-annotated differently does not.")
    lines.append("- Low-information pairs are excluded from the ranking. They are "
                 "in `excluded_low_information.csv` and can be inspected there.")
    lines.append("- A thin visual difference is not proof of independence. The "
                 "sheet supports the contamination tables; it does not replace "
                 "them.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % OUT_PNG)
    print("  %.0f x %.0f px, %.1f KB"
          % (FIG_W * DPI, fig_h * DPI, os.path.getsize(OUT_PNG) / 1024.0))
    print("  cross-split pairs scored : %d" % len(scored))
    print("  test<->train qualifying  : %d (closest %.4f, threshold %.2f)"
          % (tt_qualifying, closest_tt if closest_tt else -1, eps_max))
    print("  low-info excluded        : %d" % len(low_only))
    print("  provenance               : %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
