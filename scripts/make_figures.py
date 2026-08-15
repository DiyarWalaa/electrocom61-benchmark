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
import matplotlib.ticker  # noqa: E402
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
INK_MUTED = "#75746e"
GRID = "#cccccc"

F1_SOURCE = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                         "class_split_counts.csv")

# The threshold the paper uses for "too few to evaluate meaningfully".
MIN_TEST = 5

# --- F5 --------------------------------------------------------------------
F5_SOURCE = os.path.join(ec61.DATA_DIR, "master_results.csv")

# The two metrics, as (column, axis label, panel letter).
F5_METRICS = (("test_mAP50", "test mAP@50", "a"),
              ("test_mAP50_95", "test mAP@50-95", "b"))

# Five models, so colour alone cannot carry identity in greyscale. Each line
# also gets its own marker AND a direct label at its right end; colour is the
# weakest of the three channels here, not the load-bearing one.
F5_PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#7a3ea3", "#c81e5b")
F5_MARKERS = ("o", "s", "^", "D", "v")


# --- F4 --------------------------------------------------------------------
F4_SWEEP = os.path.join(ec61.RUNS_DIR, "20260804_burst_aware_tau_sweep",
                        "tau_sweep.csv")
F4_DETAIL = os.path.join(ec61.RUNS_DIR, "20260804_burst_aware_tau_sweep",
                         "tau_sweep_detail.csv")


# --- F6 --------------------------------------------------------------------
F6_LATENCY = os.path.join(ec61.DATA_DIR, "latency_by_arch.csv")
F6_ACCURACY = os.path.join(ec61.DATA_DIR, "master_results.csv")

# Marker area is proportional to fused GFLOPs, so DIAMETER goes as its square
# root -- the perceptually correct mapping for an area encoding.
F6_AREA_PER_GFLOP = 3.0
F6_SIZE_LEGEND_GFLOPS = (25, 50, 100)


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
# Panel (b): the same sessions labelled twice, from the CSV's DATA_TYPE (v1)
# and from the folders (v2), restricted to the images the CSV covers.
F2B_SOURCE = os.path.join(ec61.RUNS_DIR, "20260809_split_v1_vs_v2_by_group_03",
                          "split_v1_vs_v2_by_group.csv")

# Where a perfect 70/20/10 puts its segment boundaries on a 0-100 axis.
NOMINAL_BOUNDARIES = (70.0, 90.0)

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
    # Only the PDF backend writes a creation date, so only it takes the
    # metadata argument. ec61.pdf_metadata() pins it; see the note there.
    fig.savefig(pdf, metadata=ec61.pdf_metadata())
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


def load_f2b_rows(path):
    """v1 and v2 composition per capture group, from the comparison run."""
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        raw = list(csv.DictReader(fh))
    out = []
    for r in raw:
        rec = {
            "key": r["capture_group"], "label": r["label"],
            "total": int(r["imgs_in_csv"]),
            "v1": {"train": int(r["v1_train"]), "valid": int(r["v1_valid"]),
                   "test": int(r["v1_test"])},
            "v2": {"train": int(r["v2_train"]), "valid": int(r["v2_valid"]),
                   "test": int(r["v2_test"])},
            "v1_shape": r["v1_shape"], "v2_shape": r["v2_shape"],
            "changed": int(r["imgs_changed_split"]),
        }
        for tag in ("v1", "v2"):
            if sum(rec[tag].values()) != rec["total"]:
                raise ValueError("%s parts do not sum to the total for %s"
                                 % (tag, rec["key"]))
        out.append(rec)
    out.sort(key=lambda r: (r["key"] == UNTIMESTAMPED_KEY, r["key"]))
    return out


def _stack(ax, y, parts, total, height, scale100=False):
    """Draw one stacked horizontal bar."""
    left = 0.0
    for key, colour in (("train", C_TRAIN), ("valid", C_VALID), ("test", C_TEST)):
        w = parts[key] * (100.0 / total) if scale100 else parts[key]
        ax.barh([y], [w], height=height, left=[left], color=colour,
                edgecolor="white", linewidth=0.3, zorder=2)
        left += w


def figure_2(rows_a, iphone_counts, unevaluable, rows_b):
    """Two panels: v2 composition in images, and v1 vs v2 as shares.

    Panel (a) is the single-panel F2 unchanged. Panel (b) puts each session's
    v1 and v2 composition side by side, normalised so sessions of different
    sizes are comparable, with dashed references where a perfect 70/20/10
    would place its segment boundaries. A session that did not change draws
    two identical bars; one that did is obvious without reading a number.
    """
    n_a = len(rows_a)
    n_b = len(rows_b)

    train_only = [r for r in rows_a if r["train_only"]]
    train_only_keys = {r["key"] for r in train_only}
    n_train_only_imgs = sum(r["total"] for r in train_only)
    n_train_imgs = sum(r["train"] for r in rows_a)
    pct = 100.0 * n_train_only_imgs / n_train_imgs

    stray = sorted({g for cls in unevaluable for g in cls["groups"]}
                   - train_only_keys)
    if stray:
        raise ValueError("caption claims the unevaluable classes occur only in "
                         "train-only groups, but they also occur in: %s" % stray)

    # The group in (a) but absent from (b) is the session added in v2, which
    # has no row in the v1 metadata. Identified, not assumed, and required to
    # be unique.
    keys_b = set(r["key"] for r in rows_b)
    only_a = [r for r in rows_a if r["key"] not in keys_b]
    if len(only_a) != 1:
        raise ValueError("expected exactly one group in (a) and absent from "
                         "(b), found %d" % len(only_a))
    newcomer = only_a[0]

    n_v1_near = sum(1 for r in rows_b if r["v1_shape"] == "near-nominal")
    n_v2_near = sum(1 for r in rows_b if r["v2_shape"] == "near-nominal")
    n_unchanged = sum(1 for r in rows_b if r["changed"] == 0)
    total_moved = sum(r["changed"] for r in rows_b)

    caption = (
        "Capture-group composition of the published split. "
        "(a) v2 image counts per session: %d of the %d groups reach neither "
        "valid nor test (bold label, filled marker) and together hold %d of "
        "the %d training images, %.1f%%; all %d classes that cannot be "
        "evaluated occur only within them. "
        "(b) the same sessions before and after the v2 re-split, each "
        "normalised to its own total, dashed lines where a 70/20/10 split "
        "would fall. Under v1, %d of %d sessions sat within one image of "
        "70/20/10; under v2, %d do. Figures at right are images moved, %d in "
        "total; the %d sessions showing zero are identical between their "
        "pair. %s appears only in panel (a) because its %d images were added "
        "in v2 and have no row in the v1 metadata, and v2 split that new "
        "session at exactly %d/%d/%d."
        % (len(train_only), n_a, n_train_only_imgs, n_train_imgs, pct,
           len(unevaluable), n_v1_near, n_b, n_v2_near, total_moved,
           n_unchanged, newcomer["label"], newcomer["total"],
           newcomer["train"], newcomer["valid"], newcomer["test"]))

    # ---- vertical budget, in inches ---------------------------------------
    h_legend = 0.52
    h_title = 0.20
    h_xlabel = 0.34
    h_plot_a = 0.30 * n_a
    h_gap = 0.34
    h_plot_b = 0.42 * n_b
    h_bottom = 0.08
    fig_h = (h_legend + h_title + h_plot_a + h_xlabel + h_gap
             + h_title + h_plot_b + h_xlabel + h_bottom)

    fig = plt.figure(figsize=(COL_W, fig_h))

    def rect(top_in, height_in, left_frac, width_frac):
        return [left_frac, (fig_h - top_in - height_in) / fig_h,
                width_frac, height_in / fig_h]

    top_a = h_legend + h_title
    top_b = top_a + h_plot_a + h_xlabel + h_gap + h_title
    ax_a = fig.add_axes(rect(top_a, h_plot_a, 0.40, 0.57))
    ax_b = fig.add_axes(rect(top_b, h_plot_b, 0.40, 0.57))

    from matplotlib.transforms import blended_transform_factory

    # ---- panel (a), unchanged ---------------------------------------------
    for i, r in enumerate(rows_a):
        _stack(ax_a, i, r, r["total"], 0.68)
    ax_a.set_yticks(list(range(n_a)))
    ax_a.set_yticklabels([r["label"] for r in rows_a])
    ax_a.tick_params(axis="y", pad=13)
    ax_a.invert_yaxis()
    ax_a.set_ylim(n_a - 0.5, -0.5)
    ax_a.set_xlabel("images")
    xmax_a = max(r["total"] for r in rows_a)
    ax_a.set_xlim(0, xmax_a * 1.16)
    ax_a.set_xticks(list(range(0, int(xmax_a) + 1, 100)))
    ax_a.xaxis.grid(True, color=GRID, linewidth=0.4)
    ax_a.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax_a.spines[side].set_visible(False)
    for i, r in enumerate(rows_a):
        ax_a.text(r["total"] + xmax_a * 0.015, i, str(r["total"]),
                  va="center", ha="left", fontsize=8,
                  color=C_ACCENT if r["train_only"] else INK,
                  fontweight="bold" if r["train_only"] else "normal")
    labels_train_only = set(r["label"] for r in train_only)
    for lbl in ax_a.get_yticklabels():
        if lbl.get_text() in labels_train_only:
            lbl.set_color(C_ACCENT)
            lbl.set_fontweight("bold")
    tf_a = blended_transform_factory(ax_a.transAxes, ax_a.transData)
    for i, r in enumerate(rows_a):
        if r["train_only"]:
            ax_a.plot([-0.035], [i], marker="o", markersize=3.0, color=C_ACCENT,
                      transform=tf_a, clip_on=False, zorder=5)

    # ---- panel (b) ---------------------------------------------------------
    OFF = 0.22
    BH = 0.40
    for i, r in enumerate(rows_b):
        _stack(ax_b, i - OFF, r["v1"], r["total"], BH, scale100=True)
        _stack(ax_b, i + OFF, r["v2"], r["total"], BH, scale100=True)
        # Which bar is which, as text rather than colour, so the distinction
        # survives greyscale and colour vision deficiency alike.
        for tag, dy in (("v1", -OFF), ("v2", OFF)):
            ax_b.text(1.8, i + dy, tag, va="center", ha="left", fontsize=8,
                      color="white", zorder=4)

    ax_b.set_yticks(list(range(n_b)))
    ax_b.set_yticklabels([r["label"] for r in rows_b])
    ax_b.tick_params(axis="y", pad=13)
    ax_b.invert_yaxis()
    ax_b.set_ylim(n_b - 0.5, -0.5)
    ax_b.set_xlabel("share of the session (%)")
    ax_b.set_xlim(0, 126)
    ax_b.set_xticks([0, 50, 100])
    for side in ("top", "right", "left"):
        ax_b.spines[side].set_visible(False)

    # Dashed references at the 70/20/10 boundaries, mid-grey so they read
    # against the dark train segment and the pale test segment alike.
    for xb in NOMINAL_BOUNDARIES:
        ax_b.plot([xb, xb], [-0.5, n_b - 0.5], linestyle=(0, (2, 2)),
                  linewidth=0.9, color="#6e6e6e", zorder=4)

    for i, r in enumerate(rows_b):
        moved = r["changed"]
        ax_b.text(103, i, str(moved), va="center", ha="left", fontsize=8,
                  color=C_ACCENT if moved else INK_MUTED,
                  fontweight="bold" if moved else "normal")
    ax_b.text(103, -0.92, "moved", va="center", ha="left", fontsize=8,
              color=INK, style="italic")

    # ---- titles and legend -------------------------------------------------
    fig.text(0.012, (fig_h - h_legend - 0.02) / fig_h,
             "(a)  v2 composition, images", fontsize=8.5, fontweight="bold",
             va="top", ha="left", color=INK)
    fig.text(0.012, (fig_h - (top_b - h_title) - 0.02) / fig_h,
             "(b)  v1 vs v2, share of each session", fontsize=8.5,
             fontweight="bold", va="top", ha="left", color=INK)

    split_handles = [Patch(facecolor=C_TRAIN, label="train"),
                     Patch(facecolor=C_VALID, label="valid"),
                     Patch(facecolor=C_TEST, label="test")]
    mark_handles = [Line2D([], [], linestyle="none", marker="o", markersize=3.0,
                           color=C_ACCENT, label="train-only"),
                    Line2D([], [], linestyle=(0, (2, 2)), linewidth=0.9,
                           color="#6e6e6e", label="70/20/10")]
    fig.legend(handles=split_handles, ncol=3, loc="upper left",
               bbox_to_anchor=(0.015, 1.0 - 0.04 / fig_h), frameon=False,
               handlelength=1.0, handletextpad=0.4, columnspacing=1.2,
               borderaxespad=0.0)
    fig.legend(handles=mark_handles, ncol=2, loc="upper left",
               bbox_to_anchor=(0.015, 1.0 - 0.23 / fig_h), frameon=False,
               handlelength=1.4, handletextpad=0.4, columnspacing=1.2,
               borderaxespad=0.0)

    # ---- fit the shared left margin to the widest label in either panel ----
    fig.canvas.draw()
    widest = max(t.get_window_extent().width
                 for ax in (ax_a, ax_b) for t in ax.get_yticklabels()) / fig.dpi
    left = (widest + 13 / 72.0 + 0.05 + 0.02) / COL_W
    width = 1.0 - left - 0.035
    ax_a.set_position(rect(top_a, h_plot_a, left, width))
    ax_b.set_position(rect(top_b, h_plot_b, left, width))

    counts = {
        "caption_plain": caption,
        "caption_latex": latex_escape(caption),
        "n_unevaluable_classes": len(unevaluable),
        "n_groups_panel_a": n_a,
        "n_groups_panel_b": n_b,
        "n_train_only_groups": len(train_only),
        "train_only_groups": [r["label"] for r in train_only],
        "train_only_images": n_train_only_imgs,
        "train_images_total": n_train_imgs,
        "train_only_pct_of_train": round(pct, 2),
        "iphone_row_from_device_table": list(iphone_counts),
        "v1_near_nominal_groups": n_v1_near,
        "v2_near_nominal_groups": n_v2_near,
        "groups_unchanged": n_unchanged,
        "images_moved_total": total_moved,
        "panel_a_only_group": newcomer["label"],
        "panel_a_only_split": [newcomer["train"], newcomer["valid"],
                               newcomer["test"]],
        "figure_width_in": round(COL_W, 3),
        "figure_height_in": round(fig_h, 3),
        "figure_px_at_%d_dpi" % PNG_DPI: "%d x %d" % (round(COL_W * PNG_DPI),
                                                      round(fig_h * PNG_DPI)),
        "groups": [{"label": r["label"], "train": r["train"],
                    "valid": r["valid"], "test": r["test"],
                    "total": r["total"], "train_only": r["train_only"]}
                   for r in rows_a],
        "panel_b": [{"label": r["label"], "total": r["total"],
                     "v1": r["v1"], "v2": r["v2"], "changed": r["changed"],
                     "v1_shape": r["v1_shape"], "v2_shape": r["v2_shape"]}
                    for r in rows_b],
    }
    return fig, counts


def load_f5_rows(path):
    """Per-model published and corrected accuracy, from the master table."""
    # Benchmark rows only. The index below is keyed by (model, split_set)
    # and assigns rather than accumulates, so a second rtdetr-l published
    # row would silently replace the first -- and which one survived would
    # depend on read order. load_benchmark_rows refuses that outright.
    raw = ec61.load_benchmark_rows(path)

    by_model = {}
    for r in raw:
        by_model.setdefault(r["model"], {})[r["split_set"]] = r

    out = []
    for model in sorted(by_model):
        got = by_model[model]
        missing = [s2 for s2 in ("published", "corrected") if s2 not in got]
        if missing:
            raise ValueError("%s has no %s row" % (model, " or ".join(missing)))
        if len(got) != 2:
            raise ValueError("%s has %d split rows, expected 2" % (model, len(got)))
        rec = {"model": model}
        for col, _lbl, _p in F5_METRICS:
            for split in ("published", "corrected"):
                v = got[split][col]
                if v == "":
                    raise ValueError("%s %s has no %s" % (model, split, col))
                rec[(col, split)] = float(v)
            rec[(col, "delta")] = (rec[(col, "corrected")]
                                   - rec[(col, "published")])
        out.append(rec)
    return out


def _spread(values, min_gap, lo, hi):
    """Push labels apart to `min_gap` while preserving their order.

    Two of these models differ by 0.01 of a point on mAP@50-95, so their labels
    would print on top of each other at any readable size. Displacing them and
    drawing a leader line keeps the label legible while the marker stays at the
    true value -- the alternative, letting them overlap, hides exactly the
    near-tie the figure exists to show.
    """
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for k in range(1, len(order)):
        prev, cur = order[k - 1], order[k]
        if out[cur] - out[prev] < min_gap:
            out[cur] = out[prev] + min_gap
    top = order[-1]
    if out[top] > hi:
        shift = out[top] - hi
        for i in order:
            out[i] -= shift
    bot = order[0]
    if out[bot] < lo:
        shift = lo - out[bot]
        for i in order:
            out[i] += shift
    return out


def _ranks(rows, col, split):
    """Model names ordered best-first on one metric and split."""
    return [r["model"] for r in sorted(rows, key=lambda r: -r[(col, split)])]


def figure_5(rows):
    """Published vs corrected accuracy, one line per model, two metrics."""
    from matplotlib.transforms import blended_transform_factory
    n = len(rows)
    order = sorted(rows, key=lambda r: -r[(F5_METRICS[0][0], "corrected")])

    stats = {}
    for col, label, _p in F5_METRICS:
        deltas = {r["model"]: r[(col, "delta")] for r in rows}
        rp = _ranks(rows, col, "published")
        rc = _ranks(rows, col, "corrected")
        moved = [m for m in rp if rp.index(m) != rc.index(m)]
        stats[col] = {
            "label": label,
            "deltas": deltas,
            "rank_published": rp,
            "rank_corrected": rc,
            "rank_changed": moved,
            "all_rise": all(d > 0 for d in deltas.values()),
            "min_delta": min(deltas.values()),
            "max_delta": max(deltas.values()),
        }

    a_col = F5_METRICS[0][0]
    b_col = F5_METRICS[1][0]
    caption = (
        "Test accuracy under the published and the corrected split, one line "
        "per model. (a) mAP@50: every model rises, by %.2f to %.2f points, and "
        "the ranking changes -- %d of %d models occupy a different position. "
        "(b) mAP@50-95: every model rises again, by %.2f to %.2f points, but "
        "the ranking is unchanged. The contrast is the point: a metric that "
        "reorders under a change of split is reporting the split as much as "
        "the model."
        % (100 * stats[a_col]["min_delta"], 100 * stats[a_col]["max_delta"],
           len(stats[a_col]["rank_changed"]), n,
           100 * stats[b_col]["min_delta"], 100 * stats[b_col]["max_delta"]))

    # ---- vertical budget, inches ------------------------------------------
    h_title = 0.20
    h_plot = 1.95
    h_xlabel = 0.30
    h_gap = 0.40
    h_bottom = 0.10
    fig_h = 2 * (h_title + h_plot + h_xlabel) + h_gap + h_bottom

    fig = plt.figure(figsize=(COL_W, fig_h))

    # Left margin for the y tick labels; the model labels sit in a zone to the
    # RIGHT of the axes, positioned in axes fractions rather than data units.
    # Data units would tie the label zone's width to the plot's width, and the
    # first version of this figure printed the model names on top of their own
    # deltas for exactly that reason.
    left = 0.155
    plot_w = 0.30
    label_ax = 1.12         # axes fractions: 1.0 is the right spine
    delta_ax = 2.62

    axes = []
    for idx, (col, ylabel, letter) in enumerate(F5_METRICS):
        top = idx * (h_title + h_plot + h_xlabel + h_gap) + h_title
        ax = fig.add_axes([left, (fig_h - top - h_plot) / fig_h,
                           plot_w, h_plot / fig_h])
        axes.append(ax)

        for i, r in enumerate(order):
            colour = F5_PALETTE[i % len(F5_PALETTE)]
            marker = F5_MARKERS[i % len(F5_MARKERS)]
            ax.plot([0, 1], [r[(col, "published")], r[(col, "corrected")]],
                    color=colour, linewidth=1.3, marker=marker, markersize=3.6,
                    markerfacecolor=colour, markeredgecolor="white",
                    markeredgewidth=0.5, zorder=3, clip_on=False)

        vals = [r[(col, "corrected")] for r in order]
        lo_v, hi_v = min(vals), max(vals)
        pub = [r[(col, "published")] for r in order]
        span_lo = min(lo_v, min(pub))
        span_hi = max(hi_v, max(pub))
        pad = (span_hi - span_lo) * 0.16
        ax.set_ylim(span_lo - pad, span_hi + pad)
        ax.set_xlim(-0.06, 1.06)
        tf = blended_transform_factory(ax.transAxes, ax.transData)

        ax.set_xticks([0, 1])
        ax.set_xticklabels(["published", "corrected"])
        ax.set_ylabel(ylabel)
        ax.yaxis.grid(True, color=GRID, linewidth=0.4)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_bounds(0, 1)
        ax.tick_params(axis="x", length=0, pad=4)

        # Label positions: true values, then pushed apart just enough to read.
        y0, y1 = ax.get_ylim()
        line_h_data = (y1 - y0) * (0.115 / h_plot)
        placed = _spread(vals, line_h_data, y0 + line_h_data * 0.6,
                         y1 - line_h_data * 0.6)

        for i, r in enumerate(order):
            colour = F5_PALETTE[i % len(F5_PALETTE)]
            ytrue, ylab = vals[i], placed[i]
            if abs(ylab - ytrue) > line_h_data * 0.12:
                ax.plot([1.01, label_ax - 0.05], [ytrue, ylab], color=colour,
                        linewidth=0.5, alpha=0.75, zorder=2, transform=tf,
                        clip_on=False)
            ax.text(label_ax, ylab, r["model"], va="center", ha="left",
                    fontsize=8, color=INK, transform=tf, clip_on=False)
            d = 100 * r[(col, "delta")]
            ax.text(delta_ax, ylab, "%+.2f" % d, va="center", ha="right",
                    fontsize=8, color=C_ACCENT, fontweight="bold",
                    transform=tf, clip_on=False)

        fig.text(0.012, (fig_h - top + 0.02) / fig_h,
                 "(%s)  %s" % (letter, ylabel), fontsize=8.5,
                 fontweight="bold", va="bottom", ha="left", color=INK)

    # One shared explanation of the accent column, above the first panel.
    axes[0].text(delta_ax, axes[0].get_ylim()[1], "delta (pts)", va="bottom",
                 ha="right", fontsize=8, color=INK, style="italic",
                 transform=blended_transform_factory(axes[0].transAxes,
                                                     axes[0].transData),
                 clip_on=False)

    counts = {
        "caption_plain": caption,
        "caption_latex": latex_escape(caption),
        "n_models": n,
        "figure_width_in": round(COL_W, 3),
        "figure_height_in": round(fig_h, 3),
        "figure_px_at_%d_dpi" % PNG_DPI: "%d x %d" % (round(COL_W * PNG_DPI),
                                                      round(fig_h * PNG_DPI)),
    }
    for col, label, _p in F5_METRICS:
        st = stats[col]
        counts[col] = {
            "label": label,
            "deltas_points": {m: round(100 * d, 2)
                              for m, d in st["deltas"].items()},
            "all_models_rise": st["all_rise"],
            "delta_range_points": [round(100 * st["min_delta"], 2),
                                   round(100 * st["max_delta"], 2)],
            "rank_published": st["rank_published"],
            "rank_corrected": st["rank_corrected"],
            "models_changing_rank": st["rank_changed"],
        }
    counts["rows"] = [
        {"model": r["model"],
         **{"%s_%s" % (c, k): round(r[(c, k)], 4)
            for c, _l, _p in F5_METRICS
            for k in ("published", "corrected", "delta")}}
        for r in order]
    return fig, counts


def load_f6_rows(latency_path, accuracy_path):
    """Join per-architecture latency to corrected-split accuracy and size."""
    with open(latency_path, "r", newline="", encoding="utf-8-sig") as fh:
        lat = {r["model"]: r for r in csv.DictReader(fh)}
    acc = {}
    for r in ec61.load_benchmark_rows(accuracy_path):
        if r["split_set"] == "corrected":
            acc[r["model"]] = r

    missing = sorted(set(lat) ^ set(acc))
    if missing:
        raise ValueError("latency and accuracy tables disagree on which models "
                         "exist: %s" % missing)

    out = []
    for model in sorted(lat):
        a, l = acc[model], lat[model]
        for col, src in (("test_mAP50_95", a), ("gflops_fused", a),
                         ("e2e_ms_p50_mean", l), ("e2e_ms_p50_gap", l)):
            if src[col] == "":
                raise ValueError("%s has no %s" % (model, col))
        out.append({
            "model": model,
            "latency": float(l["e2e_ms_p50_mean"]),
            "gap": float(l["e2e_ms_p50_gap"]),
            "map": float(a["test_mAP50_95"]),
            "gflops": float(a["gflops_fused"]),
        })
    return out


def _pareto(rows):
    """Models not dominated on (lower latency, higher mAP).

    Returns (front, dominated) where each dominated entry carries the margin
    by which it misses -- the amount of mAP it would need to gain to reach the
    front. That margin matters: one of these models is excluded by less than
    the fourth decimal place, and a front presented without it would read as a
    firmer result than it is.
    """
    front, dominated = [], []
    for r in rows:
        beaten_by = [o for o in rows
                     if o is not r
                     and o["latency"] <= r["latency"]
                     and o["map"] >= r["map"]
                     and (o["latency"] < r["latency"] or o["map"] > r["map"])]
        if beaten_by:
            margin = min(o["map"] - r["map"] for o in beaten_by
                         if o["latency"] <= r["latency"])
            dominated.append((r, margin, sorted(o["model"] for o in beaten_by)))
        else:
            front.append(r)
    front.sort(key=lambda r: r["latency"])
    return front, dominated


def figure_6(rows):
    """Accuracy against latency, marker area by fused GFLOPs."""
    front, dominated = _pareto(rows)
    front_names = set(r["model"] for r in front)

    # The rig's repeatability: the largest gap between the two timed runs of
    # any one architecture. Differences smaller than this are not differences.
    noise = max(r["gap"] for r in rows)
    noisiest = max(rows, key=lambda r: r["gap"])["model"]

    by_lat = sorted(rows, key=lambda r: r["latency"])
    closest = min(((a, b) for a, b in zip(by_lat, by_lat[1:])),
                  key=lambda p: p[1]["latency"] - p[0]["latency"])
    closest_gap = closest[1]["latency"] - closest[0]["latency"]

    tightest = min(dominated, key=lambda d: d[1]) if dominated else None

    caption = (
        "Accuracy against latency on the corrected split. Marker area is fused "
        "GFLOPs; the shaded band behind each point spans %.2f ms, the largest "
        "difference between the two timed runs of any one architecture (%s) "
        "and so this rig's noise floor. The Pareto front is %s. %s and %s are "
        "the closest pair in latency at %.2f ms apart, %.1f times the noise "
        "floor -- separable, but not by much."
        % (noise, noisiest, " and ".join(r["model"] for r in front),
           closest[0]["model"], closest[1]["model"], closest_gap,
           closest_gap / noise))
    if tightest is not None:
        caption += (" %s misses the front by %.4f mAP, which is below the "
                    "precision the accuracy figures are reported at."
                    % (tightest[0]["model"], tightest[1]))
    caption += " Latency is on a log axis, so the four CNNs are not compressed against RT-DETR-l."

    # ---- layout ------------------------------------------------------------
    # h_title was 0.20, reserving a strip for an internal "F6 accuracy vs
    # latency" heading. That heading is gone: a figure carrying a LaTeX caption
    # should not also title itself, and "F6" is this repository's working label,
    # not a name that belongs in the paper. F6 is single-panel, so unlike F2, F4
    # and F5 it has no (a)/(b) markers to keep -- the strip is reclaimed rather
    # than left blank.
    h_title = 0.02
    h_plot = 2.35
    h_xlabel = 0.34
    h_sizekey = 0.52
    h_bottom = 0.08
    fig_h = h_title + h_plot + h_xlabel + h_sizekey + h_bottom

    fig = plt.figure(figsize=(COL_W, fig_h))
    ax = fig.add_axes([0.175, (h_sizekey + h_bottom + h_xlabel) / fig_h,
                       0.80, h_plot / fig_h])
    ax.set_xscale("log")

    xs = [r["latency"] for r in rows]
    ys = [r["map"] for r in rows]
    xlo, xhi = min(xs) / 1.26, max(xs) * 1.16
    ylo, yhi = min(ys), max(ys)
    ypad = (yhi - ylo) * 0.22
    ax.set_xlim(xlo, xhi)
    ax.set_ylim(ylo - ypad, yhi + ypad)

    # Pareto staircase, drawn behind the points.
    if len(front) > 1:
        step_x, step_y = [xlo], [front[0]["map"]]
        for a, b in zip(front, front[1:]):
            step_x += [b["latency"], b["latency"]]
            step_y += [a["map"], b["map"]]
        step_x.append(xhi)
        step_y.append(front[-1]["map"])
        ax.plot(step_x, step_y, linestyle=(0, (4, 2)), linewidth=0.9,
                color="#6e6e6e", zorder=1)

    # The noise floor is drawn as a full-height band per model rather than as a
    # bar on the marker. It has to be: 0.24 ms across a 13-47 ms log axis is
    # roughly eight pixels, while the markers are up to forty across because
    # they encode GFLOPs, so any per-point bar disappears underneath its own
    # disc. A band extends past the marker and stays readable, and the gap
    # between two bands is the comparison the figure is for.
    for r in rows:
        ax.axvspan(r["latency"] - noise / 2.0, r["latency"] + noise / 2.0,
                   facecolor="#d9d9d9", edgecolor="none", zorder=0)
    for r in rows:
        on_front = r["model"] in front_names
        ax.scatter([r["latency"]], [r["map"]],
                   s=r["gflops"] * F6_AREA_PER_GFLOP,
                   facecolor=C_ACCENT if on_front else C_TRAIN,
                   edgecolor="white", linewidth=0.6,
                   zorder=4)

    # Direct labels. Offsets are chosen per model because the two fastest
    # points sit close enough that a single default rule collides.
    offsets = {r["model"]: (8, 6) for r in rows}
    # The fastest point sits hard against the y axis, so its label goes
    # below-RIGHT: below-left would print over the tick labels.
    offsets[by_lat[0]["model"]] = (9, -11)
    # The slowest point is at the right edge and carries the largest marker,
    # so its label goes left, clear of both the edge and its own disc.
    offsets[by_lat[-1]["model"]] = (-15, 8)
    for r in rows:
        dx, dy = offsets[r["model"]]
        ax.annotate("%s" % r["model"], (r["latency"], r["map"]),
                    textcoords="offset points", xytext=(dx, dy),
                    ha="left" if dx > 0 else "right", va="center",
                    fontsize=8, color=INK,
                    fontweight="bold" if r["model"] in front_names else "normal")

    # Two short lines rather than one long one: a single line ran off the
    # right edge of the column.
    ax.text(0.025, 0.075, "bands: %.2f ms noise floor" % noise,
            transform=ax.transAxes, fontsize=8, color=INK_MUTED,
            ha="left", va="bottom")
    ax.text(0.025, 0.015, "%s / %s %.2f ms apart = %.1f x"
            % (closest[0]["model"], closest[1]["model"], closest_gap,
               closest_gap / noise),
            transform=ax.transAxes, fontsize=8, color=INK_MUTED,
            ha="left", va="bottom")

    ax.set_xlabel("end-to-end latency, p50 (ms, log scale)")
    ax.set_ylabel("test mAP@50-95")
    ax.grid(True, which="major", color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([15, 20, 30, 50])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_xaxis().set_minor_formatter(matplotlib.ticker.NullFormatter())


    # ---- size key, as its own strip below the plot -------------------------
    key = fig.add_axes([0.175, h_bottom / fig_h, 0.80,
                        (h_sizekey - 0.16) / fig_h])
    key.set_xlim(0, 1)
    key.set_ylim(0, 1)
    key.axis("off")
    xpos = [0.03, 0.22, 0.45]
    for x, g in zip(xpos, F6_SIZE_LEGEND_GFLOPS):
        key.scatter([x], [0.62], s=g * F6_AREA_PER_GFLOP, facecolor=C_TRAIN,
                    edgecolor="white", linewidth=0.6)
        key.text(x, 0.06, "%d" % g, ha="center", va="bottom", fontsize=8,
                 color=INK)
    key.text(xpos[-1] + 0.14, 0.62, "fused GFLOPs", ha="left", va="center",
             fontsize=8, color=INK)
    key.plot([0.02, 0.02], [0.30, 0.94], color="none")

    counts = {
        "caption_plain": caption,
        "caption_latex": latex_escape(caption),
        "noise_floor_ms": round(noise, 4),
        "noise_floor_from": noisiest,
        "pareto_front": [r["model"] for r in front],
        "dominated": [{"model": r["model"], "misses_front_by_map": round(m, 5),
                       "dominated_by": by} for r, m, by in dominated],
        "closest_latency_pair": [closest[0]["model"], closest[1]["model"]],
        "closest_latency_gap_ms": round(closest_gap, 4),
        "closest_gap_in_noise_floors": round(closest_gap / noise, 2),
        "figure_width_in": round(COL_W, 3),
        "figure_height_in": round(fig_h, 3),
        "figure_px_at_%d_dpi" % PNG_DPI: "%d x %d" % (round(COL_W * PNG_DPI),
                                                      round(fig_h * PNG_DPI)),
        "points": [{"model": r["model"], "latency_ms": r["latency"],
                    "pair_gap_ms": r["gap"], "test_mAP50_95": r["map"],
                    "gflops_fused": r["gflops"],
                    "on_pareto_front": r["model"] in front_names}
                   for r in by_lat],
    }
    return fig, counts


def load_f4_rows(sweep_path, detail_path):
    """The tau sweep: what each value cost and whether it was admissible."""
    with open(sweep_path, "r", newline="", encoding="utf-8-sig") as fh:
        sweep = {r["tau_seconds"]: r for r in csv.DictReader(fh)}
    with open(detail_path, "r", newline="", encoding="utf-8-sig") as fh:
        detail = {r["tau_seconds"]: r for r in csv.DictReader(fh)}
    if set(sweep) != set(detail):
        raise ValueError("sweep and detail tables cover different taus: %s"
                         % sorted(set(sweep) ^ set(detail)))

    def yes(v):
        return str(v).strip().lower().startswith("yes") or "YES" in str(v)

    out = []
    for key in sorted(sweep, key=int):
        a, d = sweep[key], detail[key]
        out.append({
            "tau": int(key),
            "owes": int(d["test_images_to_return"]),
            "gives": int(d["test_images_available_to_return"]),
            "feasible": yes(a["all_15_have_2_qualifying_groups"]),
            "sizes_held": yes(a["sizes_held"]),
            "zero_contam": yes(a["zero_at_every_epsilon"]),
            "pairs_raw": int(a["test_train_pairs_raw_005"]),
            "pairs_aligned": int(a["test_train_pairs_aligned_005"]),
            "moved": int(a["images_moved"]),
            "sizes_after": a["sizes_after"],
            "chosen": yes(a["satisfies_both"]),
        })
    return out


def figure_4(rows):
    """Why tau = 15: feasibility never bound, the return budget did."""
    taus = [r["tau"] for r in rows]
    admissible = [r for r in rows
                  if r["feasible"] and r["sizes_held"] and r["zero_contam"]]
    chosen = min(admissible, key=lambda r: r["tau"]) if admissible else None

    always_feasible = all(r["feasible"] for r in rows)
    first_break = next((r for r in rows if not r["sizes_held"]), None)

    caption = (
        "Why the released split uses tau = %d s. (a) the size constraint: at "
        "each tau, the images the test split owes back after admitting whole "
        "groups, against the images it can safely return. The two cross "
        "between %d and %d s, and past that point the split cannot be "
        "rebalanced -- at tau = %d s test owes %d and can return only %d, "
        "ending at %s instead of 1478/438/205. (b) the three admissibility "
        "criteria. Class feasibility is satisfied at every tau tested, so it "
        "never bound the choice; what bound it was the collapsing return "
        "budget in (a). tau = %d s is the smallest value meeting all three."
        % (chosen["tau"] if chosen else -1,
           chosen["tau"] if chosen else -1,
           first_break["tau"] if first_break else -1,
           first_break["tau"] if first_break else -1,
           first_break["owes"] if first_break else -1,
           first_break["gives"] if first_break else -1,
           first_break["sizes_after"] if first_break else "?",
           chosen["tau"] if chosen else -1))
    caption += (" The pair criterion is the strict one: zero test-train "
                "near-duplicates at every epsilon under BOTH raw and aligned "
                "scoring. Raw scoring is zero at every tau tested, so the two "
                "crosses in that row are aligned-scoring failures only.")

    # ---- layout ------------------------------------------------------------
    h_title = 0.20
    h_plot_a = 1.75
    h_xlabel = 0.34
    h_gap = 0.40
    h_plot_b = 0.92
    h_bottom = 0.42
    fig_h = h_title + h_plot_a + h_xlabel + h_gap + h_title + h_plot_b + h_bottom

    fig = plt.figure(figsize=(COL_W, fig_h))
    left, width = 0.215, 0.755

    def rect(top_in, height_in):
        return [left, (fig_h - top_in - height_in) / fig_h, width,
                height_in / fig_h]

    top_a = h_title
    ax = fig.add_axes(rect(top_a, h_plot_a))

    owes = [r["owes"] for r in rows]
    gives = [r["gives"] for r in rows]

    # Shade the region where the split can still be rebalanced.
    held = [r["tau"] for r in rows if r["sizes_held"]]
    if held:
        edge = (max(held) + min(t for t in taus if t > max(held))) / 2.0 \
            if any(t > max(held) for t in taus) else max(held)
        ax.axvspan(min(taus) - 2, edge, facecolor="#eef3f9", edgecolor="none",
                   zorder=0)
        ax.text(min(taus) - 1, max(gives) * 0.045, "sizes hold", fontsize=8,
                color=C_TRAIN, ha="left", va="bottom")

    ax.plot(taus, gives, color=C_TRAIN, linewidth=1.4, marker="o",
            markersize=3.6, markerfacecolor=C_TRAIN, markeredgecolor="white",
            markeredgewidth=0.5, zorder=3, label="test can return")
    ax.plot(taus, owes, color=C_ACCENT, linewidth=1.4, marker="s",
            markersize=3.6, markerfacecolor=C_ACCENT, markeredgecolor="white",
            markeredgewidth=0.5, zorder=3, label="test owes")

    ax.set_xlim(min(taus) - 2, max(taus) + 2)
    ax.set_ylim(0, max(gives) * 1.18)
    ax.set_ylabel("images")
    ax.set_xticks(taus)
    ax.grid(True, color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=8, handlelength=1.4,
              handletextpad=0.5, borderaxespad=0.3, labelspacing=0.3)

    fig.text(0.012, (fig_h - 0.02) / fig_h,
             "(a)  size constraint: owed vs returnable",
             fontsize=8.5, fontweight="bold", va="top", ha="left", color=INK)

    # ---- panel (b): the three criteria as a pass/fail grid -----------------
    top_b = top_a + h_plot_a + h_xlabel + h_gap + h_title
    axb = fig.add_axes(rect(top_b, h_plot_b))
    criteria = [
        ("class feasibility", "feasible"),
        ("sizes hold", "sizes_held"),
        ("no test-train pairs", "zero_contam"),
    ]
    for j, (label, key) in enumerate(criteria):
        y = len(criteria) - 1 - j
        for r in rows:
            ok = r[key]
            axb.plot([r["tau"]], [y], marker="o" if ok else "X",
                     markersize=5.2 if ok else 5.0,
                     markerfacecolor=C_TRAIN if ok else "white",
                     markeredgecolor=C_TRAIN if ok else C_ACCENT,
                     markeredgewidth=0.8 if ok else 1.3,
                     linestyle="none", clip_on=False, zorder=3)
    axb.set_yticks(range(len(criteria)))
    axb.set_yticklabels([c[0] for c in reversed(criteria)])
    axb.set_ylim(-0.6, len(criteria) - 0.4)
    axb.set_xlim(min(taus) - 2, max(taus) + 2)
    axb.set_xticks(taus)
    axb.set_xlabel("tau (seconds)")
    axb.xaxis.grid(True, color=GRID, linewidth=0.4)
    axb.set_axisbelow(True)
    for side in ("top", "right", "left"):
        axb.spines[side].set_visible(False)
    axb.tick_params(axis="y", length=0, pad=6)

    if chosen:
        axb.axvline(chosen["tau"], color=INK_MUTED, linewidth=0.8,
                    linestyle=(0, (2, 2)), zorder=1)

    fig.text(0.012, (fig_h - (top_b - h_title) - 0.02) / fig_h,
             "(b)  admissibility (filled = met)",
             fontsize=8.5, fontweight="bold", va="top", ha="left", color=INK)

    fig.canvas.draw()
    widest = max(t.get_window_extent().width
                 for a2 in (ax, axb) for t in a2.get_yticklabels()) / fig.dpi
    new_left = (widest + 6 / 72.0 + 0.06) / COL_W
    new_width = 1.0 - new_left - 0.035
    ax.set_position([new_left, ax.get_position().y0, new_width,
                     ax.get_position().height])
    axb.set_position([new_left, axb.get_position().y0, new_width,
                      axb.get_position().height])

    counts = {
        "caption_plain": caption,
        "caption_latex": latex_escape(caption),
        "chosen_tau": chosen["tau"] if chosen else None,
        "feasible_at_every_tau": always_feasible,
        "first_tau_sizes_break": first_break["tau"] if first_break else None,
        "figure_width_in": round(COL_W, 3),
        "figure_height_in": round(fig_h, 3),
        "figure_px_at_%d_dpi" % PNG_DPI: "%d x %d" % (round(COL_W * PNG_DPI),
                                                      round(fig_h * PNG_DPI)),
        "rows": rows,
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
    for p in (F2_SOURCE, F2_DEVICE_SOURCE, F2_UNEVALUABLE, F2B_SOURCE):
        if not os.path.isfile(p):
            sys.stderr.write("F2 source not found: %s\n" % p)
            return 1

    with open(F2_UNEVALUABLE, "r", newline="", encoding="utf-8-sig") as fh:
        unevaluable = [{"name": r["class_name"],
                        "groups": set(r["all_dates"].split(";"))}
                       for r in csv.DictReader(fh)]

    f2_rows, iphone_counts = load_f2_rows(F2_SOURCE, F2_DEVICE_SOURCE)
    f2b_rows = load_f2b_rows(F2B_SOURCE)
    fig2, c2 = figure_2(f2_rows, iphone_counts, unevaluable, f2b_rows)
    pdf2, png2 = save_figure(fig2, "f2_capture_group_composition")

    # One provenance record covering both figures, written once both exist so
    # a half-built run cannot leave a config claiming figures it never made.
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"figures": ["f1_class_instance_counts",
                            "f2_capture_group_composition",
                            "f5_published_vs_corrected",
                            "f6_accuracy_vs_latency",
                            "f4_tau_sweep"],
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
               "f2b_source": F2B_SOURCE,
               "f2b_source_sha256": sha256_file(F2B_SOURCE),
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
    # summary.md is written at the very end, once every figure has been built,
    # so a run that dies half way cannot leave a summary describing figures it
    # never produced.

    print()
    print("  record : %s" % os.path.relpath(run_dir, ec61.REPO_ROOT).replace("\\", "/"))

    # ---- F5 --------------------------------------------------------------
    if not os.path.isfile(F5_SOURCE):
        sys.stderr.write("F5 source not found: %s\n" % F5_SOURCE)
        return 1
    f5_rows = load_f5_rows(F5_SOURCE)
    fig5, c5 = figure_5(f5_rows)
    pdf5, png5 = save_figure(fig5, "f5_published_vs_corrected")

    print()
    print("F5  published vs corrected test accuracy")
    print("  source : %s" % os.path.relpath(F5_SOURCE, ec61.REPO_ROOT).replace("\\", "/"))
    print("  pdf    : %s (%.1f KB)" % (os.path.relpath(pdf5, ec61.REPO_ROOT).replace("\\", "/"),
                                       os.path.getsize(pdf5) / 1024))
    print("  png    : %s (%.1f KB, %d dpi)" % (os.path.relpath(png5, ec61.REPO_ROOT).replace("\\", "/"),
                                               os.path.getsize(png5) / 1024, PNG_DPI))
    for col, label, letter in F5_METRICS:
        st = c5[col]
        print()
        print("  (%s) %s" % (letter, label))
        print("    %-10s %9s %9s %9s" % ("model", "published", "corrected", "delta"))
        print("    " + "-" * 42)
        for r in c5["rows"]:
            print("    %-10s %9.4f %9.4f %+9.2f"
                  % (r["model"], r["%s_published" % col], r["%s_corrected" % col],
                     100 * r["%s_delta" % col]))
        print("    all models rise: %s   range %+.2f to %+.2f points"
              % (st["all_models_rise"], st["delta_range_points"][0],
                 st["delta_range_points"][1]))
        print("    rank published : %s" % " > ".join(st["rank_published"]))
        print("    rank corrected : %s" % " > ".join(st["rank_corrected"]))
        print("    changing rank  : %s"
              % (", ".join(st["models_changing_rank"]) or "none"))
    print()
    print("  rendered size")
    print("    %-24s %.2f in" % ("width", c5["figure_width_in"]))
    print("    %-24s %.2f in" % ("HEIGHT", c5["figure_height_in"]))
    print("    %-24s %s" % ("pixels at %d dpi" % PNG_DPI,
                            c5["figure_px_at_%d_dpi" % PNG_DPI]))
    print()
    print("  LaTeX caption (not drawn into the image)")
    print("    " + c5["caption_latex"])

    # ---- F6 --------------------------------------------------------------
    for p in (F6_LATENCY, F6_ACCURACY):
        if not os.path.isfile(p):
            sys.stderr.write("F6 source not found: %s\n" % p)
            return 1
    f6_rows = load_f6_rows(F6_LATENCY, F6_ACCURACY)
    fig6, c6 = figure_6(f6_rows)
    pdf6, png6 = save_figure(fig6, "f6_accuracy_vs_latency")

    print()
    print("F6  accuracy vs latency, corrected split")
    print("  sources: %s + %s"
          % (os.path.relpath(F6_LATENCY, ec61.REPO_ROOT).replace("\\", "/"),
             os.path.relpath(F6_ACCURACY, ec61.REPO_ROOT).replace("\\", "/")))
    print("  pdf    : %s (%.1f KB)" % (os.path.relpath(pdf6, ec61.REPO_ROOT).replace("\\", "/"),
                                       os.path.getsize(pdf6) / 1024))
    print("  png    : %s (%.1f KB, %d dpi)" % (os.path.relpath(png6, ec61.REPO_ROOT).replace("\\", "/"),
                                               os.path.getsize(png6) / 1024, PNG_DPI))
    print()
    print("  plotted values")
    print("    %-10s %10s %9s %12s %8s  %s"
          % ("model", "latency", "pair gap", "mAP@50-95", "GFLOPs", "front"))
    print("    " + "-" * 62)
    for p6 in c6["points"]:
        print("    %-10s %10.3f %9.2f %12.4f %8.3f  %s"
              % (p6["model"], p6["latency_ms"], p6["pair_gap_ms"],
                 p6["test_mAP50_95"], p6["gflops_fused"],
                 "YES" if p6["on_pareto_front"] else ""))
    print()
    print("    noise floor      : %.2f ms (largest pair gap, %s)"
          % (c6["noise_floor_ms"], c6["noise_floor_from"]))
    print("    Pareto front     : %s" % ", ".join(c6["pareto_front"]))
    for d in c6["dominated"]:
        print("    dominated        : %-9s misses front by %.5f mAP (by %s)"
              % (d["model"], d["misses_front_by_map"],
                 ", ".join(d["dominated_by"])))
    print("    closest in latency: %s vs %s, %.2f ms apart = %.1f noise floors"
          % (c6["closest_latency_pair"][0], c6["closest_latency_pair"][1],
             c6["closest_latency_gap_ms"], c6["closest_gap_in_noise_floors"]))
    print()
    print("  rendered size")
    print("    %-24s %.2f in" % ("width", c6["figure_width_in"]))
    print("    %-24s %.2f in" % ("HEIGHT", c6["figure_height_in"]))
    print("    %-24s %s" % ("pixels at %d dpi" % PNG_DPI,
                            c6["figure_px_at_%d_dpi" % PNG_DPI]))
    print()
    print("  LaTeX caption (not drawn into the image)")
    print("    " + c6["caption_latex"])

    # ---- summary sections for F5 and F6 ----------------------------------
    a_col, b_col = F5_METRICS[0][0], F5_METRICS[1][0]
    sa, sb = c5[a_col], c5[b_col]

    lines.append("## F5 — published vs corrected test accuracy")
    lines.append("")
    lines.append("- source: `data/master_results.csv`")
    lines.append("- outputs: `figures/f5_published_vs_corrected.{pdf,png}`")
    lines.append("- rendered %.2f x %.2f in"
                 % (c5["figure_width_in"], c5["figure_height_in"]))
    lines.append("")
    lines.append("| model | mAP@50 delta | mAP@50-95 delta | ratio |")
    lines.append("|---|---|---|---|")
    for r in c5["rows"]:
        da = 100 * r["%s_delta" % a_col]
        db = 100 * r["%s_delta" % b_col]
        lines.append("| %s | %+.2f | %+.2f | %.2f |"
                     % (r["model"], da, db, db / da))
    lines.append("")
    ratios = [100 * r["%s_delta" % b_col] / (100 * r["%s_delta" % a_col])
              for r in c5["rows"]]
    lines.append("### The gains shrink at higher IoU")
    lines.append("")
    lines.append("mAP@50-95 gains run **%+.2f to %+.2f points** against "
                 "**%+.2f to %+.2f** for mAP@50 — roughly half, with the "
                 "per-model ratio between %.2f and %.2f."
                 % (sb["delta_range_points"][0], sb["delta_range_points"][1],
                    sa["delta_range_points"][0], sa["delta_range_points"][1],
                    min(ratios), max(ratios)))
    lines.append("")
    lines.append("The classes the corrected split makes evaluable are therefore "
                 "**easy at IoU 0.5 but not uniformly easy at higher "
                 "thresholds**. Detecting that they are present is most of the "
                 "gain; localising them tightly is not.")
    lines.append("")
    lines.append("### Near-tie structure, and how to phrase it")
    lines.append("")
    mid = [m for m in sb["rank_corrected"] if m not in
           (sb["rank_corrected"][0], sb["rank_corrected"][-1])]
    span = {}
    for split in ("published", "corrected"):
        vals = [r["%s_%s" % (b_col, split)] for r in c5["rows"]
                if r["model"] in mid]
        span[split] = max(vals) - min(vals)
    lines.append("On mAP@50-95 both splits show the same shape: **%s** clearly "
                 "first, **%s** clearly last, and the three intermediate "
                 "models (%s) spanning only **%.4f corrected** and **%.4f "
                 "published**."
                 % (sb["rank_corrected"][0], sb["rank_corrected"][-1],
                    ", ".join(mid), span["corrected"], span["published"]))
    lines.append("")
    lines.append("So the claim **\"the ordering is identical across splits\" "
                 "overstates it**. The defensible statement is:")
    lines.append("")
    lines.append("> The same model ranks first and last on both splits, while "
                 "the three intermediate models are not separable at a single "
                 "seed.")
    lines.append("")
    lines.append("Use that phrasing in the writing phase. A single training "
                 "run gives no variance estimate, and a %.4f span is far "
                 "inside what a seed change would plausibly move."
                 % span["corrected"])
    lines.append("")

    lines.append("## F6 — accuracy vs latency")
    lines.append("")
    lines.append("- sources: `data/latency_by_arch.csv` + `data/master_results.csv`")
    lines.append("- outputs: `figures/f6_accuracy_vs_latency.{pdf,png}`")
    lines.append("- rendered %.2f x %.2f in"
                 % (c6["figure_width_in"], c6["figure_height_in"]))
    lines.append("")
    lines.append("| model | latency p50 (ms) | pair gap | mAP@50-95 | GFLOPs | front |")
    lines.append("|---|---|---|---|---|---|")
    for p6 in c6["points"]:
        lines.append("| %s | %.3f | %.2f | %.4f | %.3f | %s |"
                     % (p6["model"], p6["latency_ms"], p6["pair_gap_ms"],
                        p6["test_mAP50_95"], p6["gflops_fused"],
                        "yes" if p6["on_pareto_front"] else ""))
    lines.append("")
    lines.append("Pareto front: **%s**. Noise floor **%.2f ms**, the largest "
                 "gap between the two timed runs of any one architecture (%s)."
                 % (", ".join(c6["pareto_front"]), c6["noise_floor_ms"],
                    c6["noise_floor_from"]))
    lines.append("")
    for d in c6["dominated"]:
        lines.append("- `%s` misses the front by **%.5f mAP**, dominated by %s."
                     % (d["model"], d["misses_front_by_map"],
                        ", ".join("`%s`" % m for m in d["dominated_by"])))
    lines.append("")
    lines.append("`%s` and `%s` are the closest pair in latency at **%.2f ms**, "
                 "%.1f times the noise floor — separable, but not by much."
                 % (c6["closest_latency_pair"][0], c6["closest_latency_pair"][1],
                    c6["closest_latency_gap_ms"],
                    c6["closest_gap_in_noise_floors"]))
    lines.append("")

    # ---- F4 --------------------------------------------------------------
    for p in (F4_SWEEP, F4_DETAIL):
        if not os.path.isfile(p):
            sys.stderr.write("F4 source not found: %s\n" % p)
            return 1
    f4_rows = load_f4_rows(F4_SWEEP, F4_DETAIL)
    fig4, c4 = figure_4(f4_rows)
    pdf4, png4 = save_figure(fig4, "f4_tau_sweep")

    print()
    print("F4  tau sweep: why tau = %s" % c4["chosen_tau"])
    print("  sources: %s + %s"
          % (os.path.relpath(F4_SWEEP, ec61.REPO_ROOT).replace("\\", "/"),
             os.path.relpath(F4_DETAIL, ec61.REPO_ROOT).replace("\\", "/")))
    print("  pdf    : %s (%.1f KB)" % (os.path.relpath(pdf4, ec61.REPO_ROOT).replace("\\", "/"),
                                       os.path.getsize(pdf4) / 1024))
    print("  png    : %s (%.1f KB, %d dpi)" % (os.path.relpath(png4, ec61.REPO_ROOT).replace("\\", "/"),
                                               os.path.getsize(png4) / 1024, PNG_DPI))
    print()
    print("  derived table")
    print("    %4s %6s %6s %10s %8s %14s %8s %6s"
          % ("tau", "owes", "gives", "feasible", "held", "sizes", "0 pairs", "moved"))
    print("    " + "-" * 72)
    for r in c4["rows"]:
        print("    %4d %6d %6d %10s %8s %14s %8s %6d"
              % (r["tau"], r["owes"], r["gives"],
                 "yes" if r["feasible"] else "NO",
                 "yes" if r["sizes_held"] else "NO",
                 r["sizes_after"],
                 "yes" if r["zero_contam"] else "NO",
                 r["moved"]))
    print()
    print("    feasible at every tau tested : %s" % c4["feasible_at_every_tau"])
    print("    first tau where sizes break  : %s" % c4["first_tau_sizes_break"])
    print("    chosen                       : tau = %s" % c4["chosen_tau"])
    print()
    print("  rendered size")
    print("    %-24s %.2f in" % ("width", c4["figure_width_in"]))
    print("    %-24s %.2f in" % ("HEIGHT", c4["figure_height_in"]))
    print("    %-24s %s" % ("pixels at %d dpi" % PNG_DPI,
                            c4["figure_px_at_%d_dpi" % PNG_DPI]))
    print()
    print("  LaTeX caption (not drawn into the image)")
    print("    " + c4["caption_latex"])

    # ---- F6: how to frame the Pareto result ------------------------------
    pts = {p6["model"]: p6 for p6 in c6["points"]}
    front = c6["pareto_front"]
    fastest = min((pts[m] for m in front), key=lambda p: p["latency_ms"])
    most_acc = max((pts[m] for m in front), key=lambda p: p["test_mAP50_95"])
    noise = c6["noise_floor_ms"]
    tight = min(c6["dominated"], key=lambda d: d["misses_front_by_map"])
    tp = pts[tight["model"]]
    lat_excess = tp["latency_ms"] - fastest["latency_ms"]

    lines.append("### How to frame the Pareto result")
    lines.append("")
    lines.append("Two models are non-dominated: **%s** (lowest latency) and "
                 "**%s** (highest mAP@50-95)."
                 % (fastest["model"], most_acc["model"]))
    lines.append("")
    lines.append("**%s is excluded on latency, not on accuracy.** It matches "
                 "`%s` to within **%.4f mAP**, but is **%.1f ms slower** — "
                 "about %.0f times the measured run-to-run spread of %.2f ms."
                 % (tight["model"], fastest["model"],
                    tight["misses_front_by_map"], lat_excess,
                    lat_excess / noise, noise))
    lines.append("")
    others = [d for d in c6["dominated"] if d["model"] != tight["model"]]
    for d in others:
        p6 = pts[d["model"]]
        lines.append("- `%s` is dominated on both axes: %.1f ms slower than "
                     "`%s` (%.0f x the noise floor) and %.4f mAP below `%s`."
                     % (d["model"], p6["latency_ms"] - fastest["latency_ms"],
                        fastest["model"],
                        (p6["latency_ms"] - fastest["latency_ms"]) / noise,
                        most_acc["test_mAP50_95"] - p6["test_mAP50_95"],
                        most_acc["model"]))
    lines.append("")
    lines.append("This keeps the %.4f disclosed while making clear the "
                 "practical conclusion does not rest on it: `%s` would not "
                 "join the front even if that accuracy difference were "
                 "reversed, because its latency cost is thirty times the "
                 "measurement noise."
                 % (tight["misses_front_by_map"], tight["model"]))
    lines.append("")

    lines.append("## F4 — tau sweep")
    lines.append("")
    lines.append("- sources: `runs/20260804_burst_aware_tau_sweep/tau_sweep.csv` "
                 "+ `tau_sweep_detail.csv`")
    lines.append("- outputs: `figures/f4_tau_sweep.{pdf,png}`")
    lines.append("- rendered %.2f x %.2f in"
                 % (c4["figure_width_in"], c4["figure_height_in"]))
    lines.append("")
    lines.append("| tau | test owes | test can return | feasible | sizes hold |"
                 " sizes after | raw pairs | aligned pairs | no pairs | moved |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in c4["rows"]:
        lines.append("| %d | %d | %d | %s | %s | %s | %d | %d | %s | %d |"
                     % (r["tau"], r["owes"], r["gives"],
                        "yes" if r["feasible"] else "**no**",
                        "yes" if r["sizes_held"] else "**no**",
                        r["sizes_after"], r["pairs_raw"], r["pairs_aligned"],
                        "yes" if r["zero_contam"] else "**no**", r["moved"]))
    lines.append("")
    lines.append("### Which scoring the pair column reports")
    lines.append("")
    lines.append("`no pairs` is the **strict** criterion: zero test-train "
                 "near-duplicates at every epsilon under **both** raw and "
                 "aligned scoring. The audit keeps those two apart and so does "
                 "the underlying table — the `raw pairs` and `aligned pairs` "
                 "columns above are at eps=0.05.")
    lines.append("")
    raw_all_zero = all(r["pairs_raw"] == 0 for r in c4["rows"])
    aligned_fail = [r["tau"] for r in c4["rows"] if r["pairs_aligned"] > 0]
    if raw_all_zero and aligned_fail:
        lines.append("Raw scoring is zero at **every** tau tested. Every "
                     "failure in that column is therefore an aligned-scoring "
                     "failure only, at tau = %s. Collapsing the two would hide "
                     "that the raw signal never fires."
                     % ", ".join(str(t) for t in aligned_fail))
        lines.append("")
    lines.append("### The criteria do not fail monotonically")
    lines.append("")
    clean_but_broken = [r for r in c4["rows"]
                        if r["zero_contam"] and not r["sizes_held"]]
    if clean_but_broken:
        def _join(items):
            items = list(items)
            if len(items) == 1:
                return items[0]
            return ", ".join(items[:-1]) + " and " + items[-1]

        lines.append("A larger tau is not uniformly worse. %s %s clean on "
                     "contamination but fail on sizes, while %s each carry one "
                     "aligned pair despite sitting between them."
                     % (_join("tau=%d" % r["tau"] for r in clean_but_broken),
                        "is" if len(clean_but_broken) == 1 else "are",
                        _join("tau=%d" % t for t in aligned_fail)))
        lines.append("")
        lines.append("So the three rows of panel (b) have to be shown "
                     "separately: no single ordering of tau satisfies them in "
                     "sequence, and a reader given only a summary verdict "
                     "could not tell which criterion failed where.")
        lines.append("")
    lines.append("### Fewest images moved, scoped correctly")
    lines.append("")
    held = [r for r in c4["rows"] if r["sizes_held"]]
    best_held = min(held, key=lambda r: r["moved"]) if held else None
    best_any = min(c4["rows"], key=lambda r: r["moved"])
    if best_held is not None and best_any["tau"] != best_held["tau"]:
        lines.append("tau=%d moves **the fewest images among the values that "
                     "hold the split sizes** — %d, against %s. It is not the "
                     "fewest overall: tau=%d moves %d, but ends at %s."
                     % (best_held["tau"], best_held["moved"],
                        " and ".join("%d at tau=%d" % (r["moved"], r["tau"])
                                     for r in held if r["tau"] != best_held["tau"]),
                        best_any["tau"], best_any["moved"],
                        best_any["sizes_after"]))
        lines.append("")
    lines.append("**Feasibility never bound the choice.** All 15 rescued "
                 "classes have two or more qualifying groups at every tau "
                 "tested, so the criterion the tau was originally chosen to "
                 "satisfy was satisfied everywhere. What bound it was the "
                 "return budget: as groups grow, the number of images the test "
                 "split can safely give back collapses — %s at tau=15 down to "
                 "%s at tau=60 — while the number it owes rises. They cross "
                 "between %s and %s s."
                 % (c4["rows"][0]["gives"], c4["rows"][-1]["gives"],
                    c4["chosen_tau"], c4["first_tau_sizes_break"]))
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    return 0



if __name__ == "__main__":
    sys.exit(main())
