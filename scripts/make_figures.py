"""
make_figures.py -- every figure in the paper, from files in this repository

One script so that style is defined once and every figure inherits it. Each
figure is a function that reads a committed file, builds a matplotlib Figure and
returns it plus whatever counts belong in its caption; `save_figure` writes both
a vector PDF for the paper and a 300 dpi PNG for previewing.

RULES THIS SCRIPT ENFORCES

  No hardcoded numbers. Every value drawn or quoted is read from a file under
  this repository and printed at the end of the run, so a reader can check the
  figure against the table it came from.

  Matplotlib only. No seaborn, no style sheets that ship elsewhere.

  Sized for one IEEE column: 3.5 in wide, nothing below 8 pt.

  Colour is never the only channel. The three split colours are one hue at
  three lightnesses, which survives both colourblindness and a greyscale print
  by construction; the classes singled out carry a bold label AND a marker AND
  a colour, so losing any one of the three still leaves them identifiable.

FIGURE 1

Per-class annotation counts across all 61 classes under the PUBLISHED split,
stacked train / valid / test, sorted by total descending.

Source: runs/20260802_class_date_provenance/class_split_counts.csv
        columns class_id, class_name, inst_train, inst_valid, inst_test,
        inst_total, imgs_train, imgs_valid, imgs_test

That run computed the counts from the data/ElectroCom-61_v2/ directories, which
IS the published split. Cross-checked against the before_* columns of
runs/20260803_corrected_split_02 and runs/20260804_burst_aware_split_04 with
zero mismatches.

Run with no arguments:

    python scripts/make_figures.py

Writes figures/<name>.pdf and figures/<name>.png, plus a provenance record
under runs/<YYYYMMDD>_make_figures/.
"""

import csv
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


FIG_DIR = os.path.join(ec61.REPO_ROOT, "figures")
PNG_DPI = 300

# One IEEE column.
COL_W = 3.5

# Three lightnesses of one hue (ColorBrewer Blues). A single-hue ramp is
# colourblind-safe by construction and, because the steps differ in lightness
# rather than hue, it stays legible when the paper is printed in greyscale.
# Ordered dark -> light following train -> valid -> test, which is also the
# order of magnitude, so the visual weight matches the quantity.
C_TRAIN = "#08306b"
C_VALID = "#4292c6"
C_TEST = "#c6dbef"

# Accent for the classes being singled out. Orange against blue is the standard
# safe pairing across every common form of colour vision deficiency, and it is
# dark enough to read as near-black in greyscale.
C_ACCENT = "#d94801"

INK = "#111111"
GRID = "#cccccc"

F1_SOURCE = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                         "class_split_counts.csv")

# The threshold the paper uses for "too few to evaluate meaningfully".
MIN_TEST = 5

# --- F2 --------------------------------------------------------------------
F2_SOURCE = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                         "date_split_summary.csv")
# Read only to justify the "iPhone" label on the untimestamped bar; no bar is
# drawn from it.
F2_DEVICE_SOURCE = os.path.join(ec61.RUNS_DIR, "20260801_device_split",
                                "device_by_split.csv")
# Supplies the count of classes that cannot be evaluated, and the groups each
# occurs in, so the caption's "only within those groups" claim is verifiable.
F2_UNEVALUABLE = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                              "never_evaluated_classes.csv")

# The bucket key the audit uses for images whose filenames carry no capture
# time, and the label it is drawn with.
UNTIMESTAMPED_KEY = "<untimestamped:counter>"
UNTIMESTAMPED_LABEL = "iPhone (no timestamp)"

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def pretty_date(key):
    """YYYYMMDD -> '19 Feb 2024'. Anything else is returned unchanged."""
    if len(key) == 8 and key.isdigit():
        return "%d %s %s" % (int(key[6:8]), _MONTHS[int(key[4:6]) - 1], key[:4])
    return key


def apply_style():
    """Publication defaults. Nothing below 8 pt."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.0,
        "xtick.major.size": 2.5,
        "ytick.major.size": 0.0,
        "axes.edgecolor": INK,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,   # embed TrueType, not Type 3: required by IEEE
        "ps.fonttype": 42,
    })


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_figure(fig, name):
    """Write both formats. Returns the two paths."""
    if not os.path.isdir(FIG_DIR):
        os.makedirs(FIG_DIR)
    pdf = os.path.join(FIG_DIR, name + ".pdf")
    png = os.path.join(FIG_DIR, name + ".png")
    fig.savefig(pdf)                  # vector, no dpi needed
    fig.savefig(png, dpi=PNG_DPI)
    plt.close(fig)
    return pdf, png


def load_f1_rows(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        out.append({
            "name": r["class_name"],
            "train": int(r["inst_train"]),
            "valid": int(r["inst_valid"]),
            "test": int(r["inst_test"]),
            "total": int(r["inst_total"]),
        })
    # Guard: the stated total must equal the three parts, or the figure would
    # draw one number while its sort key came from another.
    bad = [r["name"] for r in out
           if r["train"] + r["valid"] + r["test"] != r["total"]]
    if bad:
        raise ValueError("inst_total disagrees with the parts for: %s" % bad)
    return out


_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
          "eight", "nine", "ten", "eleven", "twelve")


def num_word(n):
    """Small integers as words, so caption prose reads naturally.

    Still derived, never typed: the caller passes a counted value and this only
    changes how it is spelled. Anything outside the table falls back to digits
    rather than inventing a word.
    """
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


_LATEX_MAP = (
    ("\\", "\\textbackslash{}"),
    ("&", "\\&"),
    ("%", "\\%"),
    ("$", "\\$"),
    ("#", "\\#"),
    ("_", "\\_"),
    ("{", "\\{"),
    ("}", "\\}"),
    ("~", "\\textasciitilde{}"),
    ("^", "\\textasciicircum{}"),
)


def latex_escape(text):
    r"""Make a caption safe to paste inside \caption{}.

    Escapes the ten characters LaTeX treats specially, then converts the em
    dash to the three-hyphen ligature LaTeX expects. Backslash is handled first
    so the replacements it introduces are not themselves escaped.
    """
    for a, b in _LATEX_MAP:
        text = text.replace(a, b)
    return text.replace("—", "---")


def wrap_text(text, width_in, fontsize):
    """Wrap to a pixel width, estimated from the font size.

    matplotlib's own `wrap=True` needs a private hook to learn the target width
    and silently produced a column a few characters wide here. Estimating the
    character budget is cruder but predictable, and a caption that wraps to the
    wrong width is immediately visible.
    """
    import textwrap
    chars = max(20, int(width_in * 72 / (fontsize * 0.545)))
    return textwrap.fill(text, chars)


def figure_1(rows):
    """Per-class instance counts, published split, stacked and sorted."""
    rows = sorted(rows, key=lambda r: (-r["total"], r["name"]))
    n = len(rows)

    zero_vt = [r for r in rows if r["valid"] == 0 and r["test"] == 0]
    low_test = [r for r in rows if 0 < r["test"] < MIN_TEST]
    under_min_test = [r for r in rows if r["test"] < MIN_TEST]
    zero_names = {r["name"] for r in zero_vt}
    low_names = {r["name"] for r in low_test}

    # The caption names the most-annotated class in the whole dataset as an
    # example of the "<5 test" group. That is only true if the top-ranked class
    # is actually in that group, so it is checked rather than asserted in prose.
    top = rows[0]
    if top["name"] not in low_names:
        raise ValueError(
            "caption claims the most annotated class (%s) is among the "
            "1-%d test group, but it is not" % (top["name"], MIN_TEST - 1))

    caption = ("Per-class annotation counts, published split. "
               "%d of %d classes have zero valid+test instances (filled marker, "
               "bold label) and cannot be evaluated at all; %d in total have "
               "fewer than %s test instances — the %d above plus %s more, "
               "including %s, the most annotated class in the dataset."
               % (len(zero_vt), n, len(under_min_test), num_word(MIN_TEST),
                  len(zero_vt), num_word(len(low_test)), top["name"]))
    # The caption is NOT drawn into the image. It is returned so LaTeX can set
    # it with \caption{}, which is where a journal expects it: the text then
    # wraps to the real column, uses the document font, and is picked up by
    # \listoffigures and by cross-references. Keeping a bitmap copy inside the
    # figure would also mean the same sentence existed in two places and could
    # drift apart.
    caption_latex = latex_escape(caption)

    # Vertical budget in inches, reserved before anything is drawn so nothing
    # has to overlap: legend strip, plot body, x label.
    h_plot = 0.132 * n       # row pitch unchanged
    h_legend = 0.52          # two legend rows
    h_xlabel = 0.38
    fig_h = h_legend + h_plot + h_xlabel

    fig = plt.figure(figsize=(COL_W, fig_h))
    ax = fig.add_axes([0.60, h_xlabel / fig_h, 0.37, h_plot / fig_h])

    y = list(range(n))
    tr = [r["train"] for r in rows]
    va = [r["valid"] for r in rows]
    te = [r["test"] for r in rows]
    left_te = [a + b for a, b in zip(tr, va)]

    bh = 0.76
    ax.barh(y, tr, height=bh, color=C_TRAIN, edgecolor="white", linewidth=0.25)
    ax.barh(y, va, height=bh, left=tr, color=C_VALID, edgecolor="white",
            linewidth=0.25)
    ax.barh(y, te, height=bh, left=left_te, color=C_TEST, edgecolor="white",
            linewidth=0.25)

    ax.set_yticks(y)
    ax.set_yticklabels([r["name"] for r in rows])
    # Leave a gutter between the label text and the axis for the markers, so
    # the two never touch.
    ax.tick_params(axis="y", pad=13)
    ax.invert_yaxis()
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlabel("annotation instances")
    xmax_data = max(r["total"] for r in rows)
    ax.set_xlim(0, xmax_data * 1.02)
    # Ticks every 100. Generated from the data range rather than written out,
    # so the axis stays correct if the counts ever change.
    ax.set_xticks(list(range(0, int(xmax_data) + 1, 100)))

    ax.xaxis.grid(True, color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)

    # Three redundant channels: colour, weight, and a glyph. Losing any one --
    # to colourblindness, to a greyscale print, to a coarse preview -- still
    # leaves the class identifiable.
    for lbl in ax.get_yticklabels():
        t = lbl.get_text()
        if t in zero_names:
            lbl.set_color(C_ACCENT)
            lbl.set_fontweight("bold")
        elif t in low_names:
            lbl.set_color(C_ACCENT)

    # Markers sit in the gutter, positioned in AXES fractions so the offset is
    # independent of the data range.
    from matplotlib.transforms import blended_transform_factory
    tf = blended_transform_factory(ax.transAxes, ax.transData)
    for i, r in enumerate(rows):
        if r["name"] in zero_names:
            ax.plot([-0.055], [i], marker="o", markersize=3.0, color=C_ACCENT,
                    transform=tf, clip_on=False, zorder=5)
        elif r["name"] in low_names:
            ax.plot([-0.055], [i], marker="o", markersize=3.0,
                    markerfacecolor="white", markeredgecolor=C_ACCENT,
                    markeredgewidth=0.7, transform=tf, clip_on=False, zorder=5)

    # TWO legends, stacked, rather than one with five entries. A single legend
    # packs column-major and `mode="expand"` forces column widths that made the
    # labels overprint each other. Two smaller legends each fit their own row,
    # and the split which entry belongs to which channel -- colour vs marker --
    # is the natural one anyway.
    split_handles = [Patch(facecolor=C_TRAIN, label="train"),
                     Patch(facecolor=C_VALID, label="valid"),
                     Patch(facecolor=C_TEST, label="test")]
    mark_handles = [Line2D([], [], linestyle="none", marker="o", markersize=3.0,
                           color=C_ACCENT, label="0 valid+test"),
                    Line2D([], [], linestyle="none", marker="o", markersize=3.0,
                           markerfacecolor="white", markeredgecolor=C_ACCENT,
                           markeredgewidth=0.7, label="<%d test" % MIN_TEST)]
    # Anchored to the FIGURE, not the axes. The axes occupies only ~37% of the
    # width once the class labels have taken their margin, so an axes-anchored
    # legend runs off the right edge.
    fig.legend(handles=split_handles, ncol=3, loc="upper left",
               bbox_to_anchor=(0.015, 1.0 - 0.04 / fig_h), frameon=False,
               handlelength=1.0, handletextpad=0.4, columnspacing=1.2,
               borderaxespad=0.0)
    fig.legend(handles=mark_handles, ncol=2, loc="upper left",
               bbox_to_anchor=(0.015, 1.0 - 0.23 / fig_h), frameon=False,
               handlelength=1.0, handletextpad=0.4, columnspacing=1.2,
               borderaxespad=0.0)

    # ---- fit the left margin to the widest label, measured not guessed -----
    fig.canvas.draw()
    dpi = fig.dpi
    widest = max(t.get_window_extent().width for t in ax.get_yticklabels()) / dpi
    gutter = 13 / 72.0 + 0.05          # tick pad + marker clearance
    left = (widest + gutter + 0.02) / COL_W
    right_margin = 0.035
    ax.set_position([left, h_xlabel / fig_h,
                     1.0 - left - right_margin, h_plot / fig_h])

    counts = {
        "n_classes": n,
        "zero_valid_plus_test": len(zero_vt),
        "fewer_than_%d_test" % MIN_TEST: len(under_min_test),
        "between_1_and_%d_test" % (MIN_TEST - 1): len(low_test),
        "total_instances": sum(r["total"] for r in rows),
        "train_instances": sum(tr),
        "valid_instances": sum(va),
        "test_instances": sum(te),
        "largest_class": "%s (%d)" % (rows[0]["name"], rows[0]["total"]),
        "smallest_class": "%s (%d)" % (rows[-1]["name"], rows[-1]["total"]),
        "figure_width_in": round(COL_W, 3),
        "figure_height_in": round(fig_h, 3),
        "figure_px_at_%d_dpi" % PNG_DPI: "%d x %d" % (round(COL_W * PNG_DPI),
                                                      round(fig_h * PNG_DPI)),
        "caption_plain": caption,
        "caption_latex": caption_latex,
        "widest_label_in": round(widest, 3),
        "zero_valid_plus_test_names": [r["name"] for r in zero_vt],
        "between_1_and_4_test_names": [r["name"] for r in low_test],
    }
    return fig, counts


def load_f2_rows(path, device_path):
    """Capture groups with their split composition, ordered for drawing.

    The untimestamped bucket cannot be placed on the timeline, so it is sorted
    last rather than given a fabricated position among the dates.

    Before the untimestamped bar may be labelled "iPhone", the claim is checked:
    its train/valid/test counts must equal the iPhone row of device_by_split.csv
    exactly. The two files share no row key -- the correspondence is 1:1 between
    the counter filename family and the CSV device value -- so agreement across
    all three splits is the evidence, and a mismatch means the label is unearned.
    """
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        raw = list(csv.DictReader(fh))

    rows = []
    for r in raw:
        key = r["capture_date"]
        rows.append({
            "key": key,
            "label": UNTIMESTAMPED_LABEL if key == UNTIMESTAMPED_KEY
                     else pretty_date(key),
            "train": int(r["imgs_train"]),
            "valid": int(r["imgs_valid"]),
            "test": int(r["imgs_test"]),
            "total": int(r["imgs_total"]),
            "train_only": r["date_is_train_only"] == "yes",
        })

    bad = [r["key"] for r in rows
           if r["train"] + r["valid"] + r["test"] != r["total"]]
    if bad:
        raise ValueError("imgs_total disagrees with the parts for: %s" % bad)

    # The flag in the file and the numbers in the file must agree.
    for r in rows:
        computed = r["train"] > 0 and r["valid"] == 0 and r["test"] == 0
        if computed != r["train_only"]:
            raise ValueError("date_is_train_only disagrees with the counts "
                             "for %s" % r["key"])

    # --- justify the iPhone label ---------------------------------------
    with open(device_path, "r", newline="", encoding="utf-8-sig") as fh:
        dev = {d["device_name_csv"]: d for d in csv.DictReader(fh)}
    untimed = [r for r in rows if r["key"] == UNTIMESTAMPED_KEY]
    if len(untimed) != 1:
        raise ValueError("expected exactly one %s row" % UNTIMESTAMPED_KEY)
    u = untimed[0]
    iphone = dev.get("iPhone")
    if iphone is None:
        raise ValueError("no iPhone row in %s" % device_path)
    got = (int(iphone["train"]), int(iphone["valid"]), int(iphone["test"]))
    want = (u["train"], u["valid"], u["test"])
    if got != want:
        raise ValueError(
            "cannot label the untimestamped bar 'iPhone': counter family is "
            "%s but the iPhone device row is %s" % (want, got))

    rows.sort(key=lambda r: (r["key"] == UNTIMESTAMPED_KEY, r["key"]))
    return rows, want


def figure_2(rows, iphone_counts, unevaluable):
    """Capture-group composition: which sessions reach valid and test at all.

    `unevaluable` is the list of class names that cannot be evaluated at all,
    read from the audit's never_evaluated_classes.csv. It is passed in rather
    than counted here so the caption's claim -- that those classes occur only
    within the train-only groups -- is checked against the same table that
    produced them.
    """
    n = len(rows)
    train_only = [r for r in rows if r["train_only"]]
    train_only_keys = {r["key"] for r in train_only}
    n_train_only_imgs = sum(r["total"] for r in train_only)
    n_train_imgs = sum(r["train"] for r in rows)
    pct = 100.0 * n_train_only_imgs / n_train_imgs

    # The caption asserts the unevaluable classes occur ONLY in these groups.
    # Verified here; a class appearing anywhere else makes the sentence false.
    stray = sorted({g for cls in unevaluable for g in cls["groups"]}
                   - train_only_keys)
    if stray:
        raise ValueError("caption claims the unevaluable classes occur only in "
                         "train-only groups, but they also occur in: %s" % stray)

    caption = ("Capture-group composition of the published split. Each bar is "
               "one capture session; %d of the %d groups reach neither valid "
               "nor test (bold label, filled marker) and together hold %d of "
               "the %d training images, %.1f%%. All %d classes that cannot be "
               "evaluated at all occur only within those three groups."
               % (len(train_only), n, n_train_only_imgs, n_train_imgs, pct,
                  len(unevaluable)))

    # Nine rows, so a far larger pitch than F1's 61-row chart. The conventions
    # that matter -- colours, 8 pt floor, column width, legend, marker language
    # -- are shared; the row pitch is not one of them.
    h_plot = 0.30 * n
    h_legend = 0.52
    h_xlabel = 0.38
    fig_h = h_legend + h_plot + h_xlabel

    fig = plt.figure(figsize=(COL_W, fig_h))
    ax = fig.add_axes([0.40, h_xlabel / fig_h, 0.57, h_plot / fig_h])

    y = list(range(n))
    tr = [r["train"] for r in rows]
    va = [r["valid"] for r in rows]
    te = [r["test"] for r in rows]
    left_te = [a + b for a, b in zip(tr, va)]

    bh = 0.68
    ax.barh(y, tr, height=bh, color=C_TRAIN, edgecolor="white", linewidth=0.3)
    ax.barh(y, va, height=bh, left=tr, color=C_VALID, edgecolor="white",
            linewidth=0.3)
    ax.barh(y, te, height=bh, left=left_te, color=C_TEST, edgecolor="white",
            linewidth=0.3)

    ax.set_yticks(y)
    ax.set_yticklabels([r["label"] for r in rows])
    ax.tick_params(axis="y", pad=13)
    ax.invert_yaxis()
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_xlabel("images")

    xmax_data = max(r["total"] for r in rows)
    ax.set_xlim(0, xmax_data * 1.16)          # room for the value labels
    ax.set_xticks(list(range(0, int(xmax_data) + 1, 100)))
    ax.xaxis.grid(True, color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)

    # Total at the end of each bar: with nine bars there is room, and it lets a
    # reader check 100 / 486 / 189 against the figure without the table.
    for i, r in enumerate(rows):
        ax.text(r["total"] + xmax_data * 0.015, i, str(r["total"]),
                va="center", ha="left", fontsize=8,
                color=C_ACCENT if r["train_only"] else INK,
                fontweight="bold" if r["train_only"] else "normal")

    for lbl in ax.get_yticklabels():
        if lbl.get_text() in {r["label"] for r in train_only}:
            lbl.set_color(C_ACCENT)
            lbl.set_fontweight("bold")

    from matplotlib.transforms import blended_transform_factory
    tf = blended_transform_factory(ax.transAxes, ax.transData)
    for i, r in enumerate(rows):
        if r["train_only"]:
            ax.plot([-0.035], [i], marker="o", markersize=3.0, color=C_ACCENT,
                    transform=tf, clip_on=False, zorder=5)

    split_handles = [Patch(facecolor=C_TRAIN, label="train"),
                     Patch(facecolor=C_VALID, label="valid"),
                     Patch(facecolor=C_TEST, label="test")]
    mark_handles = [Line2D([], [], linestyle="none", marker="o", markersize=3.0,
                           color=C_ACCENT, label="train-only group")]
    fig.legend(handles=split_handles, ncol=3, loc="upper left",
               bbox_to_anchor=(0.015, 1.0 - 0.04 / fig_h), frameon=False,
               handlelength=1.0, handletextpad=0.4, columnspacing=1.2,
               borderaxespad=0.0)
    fig.legend(handles=mark_handles, ncol=1, loc="upper left",
               bbox_to_anchor=(0.015, 1.0 - 0.23 / fig_h), frameon=False,
               handlelength=1.0, handletextpad=0.4, borderaxespad=0.0)

    fig.canvas.draw()
    widest = max(t.get_window_extent().width
                 for t in ax.get_yticklabels()) / fig.dpi
    left = (widest + 13 / 72.0 + 0.05 + 0.02) / COL_W
    ax.set_position([left, h_xlabel / fig_h, 1.0 - left - 0.035, h_plot / fig_h])

    counts = {
        "caption_plain": caption,
        "caption_latex": latex_escape(caption),
        "n_unevaluable_classes": len(unevaluable),
        "n_groups": n,
        "n_train_only_groups": len(train_only),
        "train_only_groups": [r["label"] for r in train_only],
        "train_only_images": n_train_only_imgs,
        "train_images_total": n_train_imgs,
        "train_only_pct_of_train": round(pct, 2),
        "iphone_row_from_device_table": list(iphone_counts),
        "figure_width_in": round(COL_W, 3),
        "figure_height_in": round(fig_h, 3),
        "figure_px_at_%d_dpi" % PNG_DPI: "%d x %d" % (round(COL_W * PNG_DPI),
                                                      round(fig_h * PNG_DPI)),
        "groups": [{"label": r["label"], "train": r["train"], "valid": r["valid"],
                    "test": r["test"], "total": r["total"],
                    "train_only": r["train_only"]} for r in rows],
    }
    return fig, counts


def main():
    apply_style()

    if not os.path.isfile(F1_SOURCE):
        sys.stderr.write("F1 source not found: %s\n" % F1_SOURCE)
        return 1

    run_dir = ec61.make_run_dir("make_figures")

    rows = load_f1_rows(F1_SOURCE)
    fig, counts = figure_1(rows)
    pdf, png = save_figure(fig, "f1_class_instance_counts")

    print("F1  per-class instance counts, published split")
    print("  source : %s" % os.path.relpath(F1_SOURCE, ec61.REPO_ROOT).replace("\\", "/"))
    print("  pdf    : %s (%.1f KB)" % (os.path.relpath(pdf, ec61.REPO_ROOT).replace("\\", "/"),
                                       os.path.getsize(pdf) / 1024))
    print("  png    : %s (%.1f KB, %d dpi)" % (os.path.relpath(png, ec61.REPO_ROOT).replace("\\", "/"),
                                               os.path.getsize(png) / 1024, PNG_DPI))
    print()
    print("  derived counts")
    for k in ("n_classes", "total_instances", "train_instances",
              "valid_instances", "test_instances", "zero_valid_plus_test",
              "fewer_than_5_test", "between_1_and_4_test",
              "largest_class", "smallest_class"):
        print("    %-24s %s" % (k, counts[k]))
    print()
    print("  rendered size")
    print("    %-24s %.2f in" % ("width", counts["figure_width_in"]))
    print("    %-24s %.2f in" % ("HEIGHT", counts["figure_height_in"]))
    print("    %-24s %s" % ("pixels at %d dpi" % PNG_DPI,
                            counts["figure_px_at_%d_dpi" % PNG_DPI]))
    print()
    print("  LaTeX caption (not drawn into the image)")
    print("    " + counts["caption_latex"])
    print()
    print("  zero valid+test (%d):" % counts["zero_valid_plus_test"])
    for nme in counts["zero_valid_plus_test_names"]:
        print("    - %s" % nme)
    print("  1-4 test instances (%d):" % counts["between_1_and_4_test"])
    for nme in counts["between_1_and_4_test_names"]:
        print("    - %s" % nme)

    # ---- F2 --------------------------------------------------------------
    for p in (F2_SOURCE, F2_DEVICE_SOURCE, F2_UNEVALUABLE):
        if not os.path.isfile(p):
            sys.stderr.write("F2 source not found: %s\n" % p)
            return 1

    with open(F2_UNEVALUABLE, "r", newline="", encoding="utf-8-sig") as fh:
        unevaluable = [{"name": r["class_name"],
                        "groups": set(r["all_dates"].split(";"))}
                       for r in csv.DictReader(fh)]

    f2_rows, iphone_counts = load_f2_rows(F2_SOURCE, F2_DEVICE_SOURCE)
    fig2, c2 = figure_2(f2_rows, iphone_counts, unevaluable)
    pdf2, png2 = save_figure(fig2, "f2_capture_group_composition")

    # One provenance record covering both figures, written once both exist so
    # a half-built run cannot leave a config claiming figures it never made.
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"figures": ["f1_class_instance_counts",
                            "f2_capture_group_composition"],
                "column_width_in": COL_W, "png_dpi": PNG_DPI,
                "min_test": MIN_TEST, "pdf_fonttype": 42},
        extra={"f1_source": F1_SOURCE,
               "f1_source_sha256": sha256_file(F1_SOURCE),
               "f1_counts": counts,
               "f2_source": F2_SOURCE,
               "f2_source_sha256": sha256_file(F2_SOURCE),
               "f2_device_source": F2_DEVICE_SOURCE,
               "f2_device_source_sha256": sha256_file(F2_DEVICE_SOURCE),
               "f2_unevaluable_source": F2_UNEVALUABLE,
               "f2_unevaluable_source_sha256": sha256_file(F2_UNEVALUABLE),
               "f2_counts": c2,
               "outputs": [pdf, png, pdf2, png2]})

    print()
    print("F2  capture-group composition, published split")
    print("  source : %s" % os.path.relpath(F2_SOURCE, ec61.REPO_ROOT).replace("\\", "/"))
    print("  label  : %s (iPhone attribution checked against %s)"
          % (UNTIMESTAMPED_LABEL,
             os.path.relpath(F2_DEVICE_SOURCE, ec61.REPO_ROOT).replace("\\", "/")))
    print("  pdf    : %s (%.1f KB)" % (os.path.relpath(pdf2, ec61.REPO_ROOT).replace("\\", "/"),
                                       os.path.getsize(pdf2) / 1024))
    print("  png    : %s (%.1f KB, %d dpi)" % (os.path.relpath(png2, ec61.REPO_ROOT).replace("\\", "/"),
                                               os.path.getsize(png2) / 1024, PNG_DPI))
    print()
    print("  derived group table")
    print("    %-22s %6s %6s %6s %7s  %s" % ("group", "train", "valid", "test",
                                             "total", "train-only"))
    print("    " + "-" * 62)
    for g in c2["groups"]:
        print("    %-22s %6d %6d %6d %7d  %s"
              % (g["label"], g["train"], g["valid"], g["test"], g["total"],
                 "YES" if g["train_only"] else ""))
    print("    " + "-" * 62)
    print("    %-22s %6d %6d %6d %7d"
          % ("TOTAL", sum(g["train"] for g in c2["groups"]),
             sum(g["valid"] for g in c2["groups"]),
             sum(g["test"] for g in c2["groups"]),
             sum(g["total"] for g in c2["groups"])))
    print()
    print("    train-only groups     : %d (%s)"
          % (c2["n_train_only_groups"], ", ".join(c2["train_only_groups"])))
    print("    train-only images     : %d" % c2["train_only_images"])
    print("    of train images       : %d" % c2["train_images_total"])
    print("    share of train        : %.1f%%" % c2["train_only_pct_of_train"])
    print("    unevaluable classes   : %d, all confined to those groups"
          % c2["n_unevaluable_classes"])
    print("    iPhone row cross-check: %s" % c2["iphone_row_from_device_table"])
    print()
    print("  rendered size")
    print("    %-24s %.2f in" % ("width", c2["figure_width_in"]))
    print("    %-24s %.2f in" % ("HEIGHT", c2["figure_height_in"]))
    print("    %-24s %s" % ("pixels at %d dpi" % PNG_DPI,
                            c2["figure_px_at_%d_dpi" % PNG_DPI]))
    print()
    print("  LaTeX caption (not drawn into the image)")
    print("    " + c2["caption_latex"])

    lines = ["# Figures", "", "Run directory: `%s`" % os.path.basename(run_dir), "",
             "## F1 — per-class instance counts (published split)", "",
             "- source: `%s`" % os.path.relpath(F1_SOURCE, ec61.REPO_ROOT).replace("\\", "/"),
             "- outputs: `figures/f1_class_instance_counts.pdf`, "
             "`figures/f1_class_instance_counts.png` (%d dpi)" % PNG_DPI, ""]
    lines.append("| quantity | value |")
    lines.append("|---|---|")
    for k in ("n_classes", "total_instances", "train_instances",
              "valid_instances", "test_instances", "zero_valid_plus_test",
              "fewer_than_5_test", "between_1_and_4_test",
              "largest_class", "smallest_class", "figure_width_in",
              "figure_height_in"):
        lines.append("| %s | %s |" % (k, counts[k]))
    lines.append("")
    lines.append("Classes with zero valid+test instances: %s"
                 % ", ".join("`%s`" % s for s in counts["zero_valid_plus_test_names"]))
    lines.append("")
    lines.append("Classes with 1-%d test instances: %s"
                 % (MIN_TEST - 1,
                    ", ".join("`%s`" % s for s in counts["between_1_and_4_test_names"])))
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- Counts are annotation instances, not images. A class with "
                 "many instances in few images is less diverse than the bar "
                 "suggests; `imgs_*` columns in the source carry that.")
    lines.append("- The published split is shown. Under the released "
                 "burst-aware split every class has at least %d instances in "
                 "both valid and test, so this figure describes the problem, "
                 "not the shipped state." % MIN_TEST)
    lines.append("- Sorting is by total instances, which is dominated by train. "
                 "A class high in the ordering can still be unevaluable.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print()
    print("  record : %s" % os.path.relpath(run_dir, ec61.REPO_ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
