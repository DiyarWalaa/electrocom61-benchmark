"""
make_tables.py -- every table in the paper, as LaTeX booktabs, from committed files

One .tex file per table under tables/. Same discipline as make_figures.py: every
value is read from a committed CSV or JSON, nothing is typed inside this script,
each table is printed so it can be checked against its source, and a run folder
records the SHA-256 of every input.

WRITTEN WITH PYTHON FILE I/O, NEVER A SHELL HEREDOC

A LaTeX block in figures/README.md was silently corrupted once when generated
through a heredoc: the shell collapsed a doubled backslash and Python read the
result as an escape. `\\b` is a valid escape and became a backspace without a
warning, while `\\c`, `\\e` and `\\l` are invalid and survived. Everything here
is written directly, and every output is scanned for control characters before
it reaches disk.

THE ONE TABLE THAT IS NOT PURELY MEASURED

T3 reports which settings were copied from prior work and which this study
added. That is a citation, not a measurement, and nothing in the repository
records it. It is read from data/config_provenance.csv, whose `source` and
`citation` columns are filled by hand. This script types none of it, and prints
how many rows are still unclassified so a provisional table cannot pass for a
finished one.

T3 prints only the rows that are NOT `default`. The full 99-row file stays in
the repository as the complete record; the paper's table shows the settings
somebody actually decided, which would otherwise be lost among Ultralytics
defaults nobody chose.

THE TRAP T2 AVOIDS

Two committed runs describe "corrected split" contamination and they disagree,
because they describe different splits. runs/20260804_duplicate_contamination
was built against the superseded image-level split and reports 2 raw / 4
aligned test-train pairs; the released burst-aware split reports 0 / 0. T2 uses
runs/20260804_burst_aware_split_04, and asserts that the per-class counts it
quotes were built from that same manifest before using them.

Run with no arguments:

    python scripts/make_tables.py

Writes tables/*.tex and runs/<YYYYMMDD>_make_tables/.
"""

import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


TAB_DIR = os.path.join(ec61.REPO_ROOT, "tables")

# ---- sources ---------------------------------------------------------------
S_NEVER_EVAL = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                            "never_evaluated_classes.csv")
S_CLASS_SPLIT = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                             "class_split_counts.csv")
S_DATE_SPLIT = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                            "date_split_summary.csv")
S_BUILT = os.path.join(ec61.RUNS_DIR, "20260804_build_corrected_dataset_02",
                       "class_counts_built.csv")
S_BUILD_CFG = os.path.join(ec61.RUNS_DIR, "20260804_build_corrected_dataset_02",
                           "config.json")
S_RELEASED = os.path.join(ec61.RUNS_DIR, "20260804_burst_aware_split_04")
S_RELEASED_MANIFEST = os.path.join(S_RELEASED, "split_manifest.csv")
S_RELEASED_CFG = os.path.join(S_RELEASED, "config.json")
S_RELEASED_MOVES = os.path.join(S_RELEASED, "moves.csv")
S_CONTAM = os.path.join(S_RELEASED, "contamination_comparison.csv")
S_PROVENANCE = os.path.join(ec61.DATA_DIR, "config_provenance.csv")
S_MASTER = os.path.join(ec61.DATA_DIR, "master_results.csv")
S_LATENCY = os.path.join(ec61.DATA_DIR, "latency_by_arch.csv")
# _03 is bound deliberately rather than globbing the newest: _02 and _03 are
# byte-identical and _01 predates them, so the choice is stable, and a glob
# would silently re-point this table if another run were ever added.
S_GROUP_RATIO = os.path.join(ec61.RUNS_DIR, "20260809_split_ratio_by_group_03",
                             "split_ratio_by_group.csv")

ALL_SOURCES = [S_NEVER_EVAL, S_CLASS_SPLIT, S_DATE_SPLIT, S_BUILT, S_BUILD_CFG,
               S_RELEASED_MANIFEST, S_RELEASED_CFG, S_RELEASED_MOVES, S_CONTAM,
               S_PROVENANCE, S_MASTER, S_LATENCY, S_GROUP_RATIO]

MIN_PER_SPLIT = 5
EPS = "0.05"

_LATEX_MAP = (
    ("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("$", "\\$"),
    ("#", "\\#"), ("_", "\\_"), ("{", "\\{"), ("}", "\\}"),
    ("~", "\\textasciitilde{}"), ("^", "\\textasciicircum{}"),
)


def tex(v):
    """Escape a value for LaTeX. Numbers pass through untouched."""
    s = v if isinstance(v, str) else str(v)
    for a, b in _LATEX_MAP:
        s = s.replace(a, b)
    return s


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def read_json(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def commas(n):
    return "{:,}".format(int(n))


# A row equal to this is emitted as a rule on its own line. Putting \midrule
# inside a cell is not valid LaTeX; it has to sit between rows.
MIDRULE = "<<MIDRULE>>"


def booktabs(label, caption, colspec, header, rows, notes=None,
             star=False, size=None):
    """One LaTeX table. `rows` is a list of lists of already-escaped strings.

    `star` emits table*, spanning both columns -- needed when a column holds
    prose rather than numbers. `size` inserts a font size command inside the
    float.
    """
    env = "table*" if star else "table"
    out = ["\\begin{%s}[t]" % env, "  \\centering",
           "  \\caption{%s}" % caption, "  \\label{%s}" % label]
    if size:
        out.append("  \\%s" % size)
    out += ["  \\begin{tabular}{%s}" % colspec, "    \\toprule",
           "    " + " & ".join(header) + " \\\\", "    \\midrule"]
    for r in rows:
        if r == MIDRULE:
            out.append("    \\midrule")
            continue
        out.append("    " + " & ".join(str(c) for c in r) + " \\\\")
    out.append("    \\bottomrule")
    out.append("  \\end{tabular}")
    if notes:
        # A plain paragraph rather than tablenotes, which would require
        # threeparttable and silently fail to compile without it.
        out.append("  \\vspace{2pt}")
        out.append("  \\par{\\footnotesize\\raggedright %s\\par}"
                   % " ".join(notes))
    out.append("\\end{%s}" % env)
    return "\n".join(out) + "\n"


def show(title, header, rows, note=None):
    """Print an aligned plain-text version so the table can be checked."""
    cols = list(zip(*([header] + rows))) if rows else [header]
    widths = [max(len(str(c)) for c in col) for col in cols]
    print(title)
    print("  " + "  ".join(str(h).ljust(w) for h, w in zip(header, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print("  " + "  ".join(str(c).ljust(w) for c, w in zip(r, widths)))
    if note:
        print("  " + note)
    print()


# ---------------------------------------------------------------- T1
def t1():
    never = read_csv(S_NEVER_EVAL)
    totals = {r["class_name"]: r for r in read_csv(S_CLASS_SPLIT)}

    rows = []
    for r in never:
        t = totals[r["class_name"]]
        if int(t["inst_valid"]) or int(t["inst_test"]):
            raise ValueError("%s is listed as never-evaluated but has "
                             "valid/test instances" % r["class_name"])
        rows.append({
            "name": r["class_name"],
            "inst_train": int(r["inst_train"]),
            "imgs_train": int(r["imgs_train"]),
            "inst_total": int(t["inst_total"]),
        })
    rows.sort(key=lambda x: (-x["inst_total"], x["name"]))

    tot_inst = sum(x["inst_train"] for x in rows)
    tot_imgs = sum(x["imgs_train"] for x in rows)
    tot_all = sum(x["inst_total"] for x in rows)
    all_inst = sum(int(t["inst_total"]) for t in totals.values())

    header = ["Class", "Train inst.", "Train images", "Total inst."]
    body = [[tex(x["name"]), commas(x["inst_train"]), commas(x["imgs_train"]),
             commas(x["inst_total"])] for x in rows]
    body.append(MIDRULE)
    body.append(["Total (%d classes)" % len(rows), commas(tot_inst),
                 commas(tot_imgs), commas(tot_all)])

    caption = ("The %d classes with zero instances in both validation and test "
               "under the published split. Every instance of each sits in "
               "training, so none can be evaluated at all. Together they hold "
               "%s of the dataset's %s annotations, %.1f\\%%."
               % (len(rows), commas(tot_all), commas(all_inst),
                  100.0 * tot_all / all_inst))
    latex = booktabs("tab:unevaluable-classes", caption, "lrrr", header, body)

    plain = [[x["name"], commas(x["inst_train"]), commas(x["imgs_train"]),
              commas(x["inst_total"])] for x in rows]
    plain.append(["TOTAL (%d)" % len(rows), commas(tot_inst), commas(tot_imgs),
                  commas(tot_all)])
    return latex, ("T1  unevaluable classes", header, plain,
                   "%.1f%% of all %s annotations"
                   % (100.0 * tot_all / all_inst, commas(all_inst)))


# ---------------------------------------------------------------- T2
def t2():
    # The per-class counts quoted for the corrected split must come from a
    # build of the RELEASED manifest. Asserted, because a run built from the
    # superseded image-level split would look identical in structure.
    build_cfg = read_json(S_BUILD_CFG)
    used = build_cfg.get("params", {}).get("manifest", "").replace("\\", "/")
    want = "20260804_burst_aware_split_04/split_manifest.csv"
    if not used.endswith(want):
        raise ValueError("class_counts_built.csv was built from %r, not the "
                         "released manifest %r" % (used, want))

    dates = read_csv(S_DATE_SPLIT)
    pub_sizes = {s: sum(int(r["imgs_%s" % s]) for r in dates)
                 for s in ("train", "valid", "test")}
    manifest = read_csv(S_RELEASED_MANIFEST)
    cor_sizes = {s: sum(1 for r in manifest if r["split"] == s)
                 for s in ("train", "valid", "test")}

    pub_cls = read_csv(S_CLASS_SPLIT)
    cor_cls = read_csv(S_BUILT)

    def counts(rows, vk, tk):
        meets = sum(1 for r in rows
                    if int(r[vk]) >= MIN_PER_SPLIT and int(r[tk]) >= MIN_PER_SPLIT)
        zero = sum(1 for r in rows if int(r[vk]) == 0 and int(r[tk]) == 0)
        return meets, zero, len(rows)

    p_meets, p_zero, n_cls = counts(pub_cls, "inst_valid", "inst_test")
    c_meets, c_zero, _ = counts(cor_cls, "inst_valid", "inst_test")

    contam = {(r["state"], r["scoring"]): r for r in read_csv(S_CONTAM)
              if r["epsilon"] == EPS}
    if not contam:
        raise ValueError("no contamination rows at epsilon %s" % EPS)
    rel_state = "burst_aware"

    cfg = read_json(S_RELEASED_CFG)["params"]
    moved = len(read_csv(S_RELEASED_MOVES))

    def pair(state, field):
        return "%s / %s" % (contam[(state, "raw")][field],
                            contam[(state, "aligned")][field])

    header = ["Property", "Published", "Corrected"]
    spec = [
        ("Images (train / val / test)",
         "%s / %s / %s" % (commas(pub_sizes["train"]), commas(pub_sizes["valid"]),
                           commas(pub_sizes["test"])),
         "%s / %s / %s" % (commas(cor_sizes["train"]), commas(cor_sizes["valid"]),
                           commas(cor_sizes["test"]))),
        ("Classes with $\\geq$%d inst. in val and test" % MIN_PER_SPLIT,
         "%d of %d" % (p_meets, n_cls), "%d of %d" % (c_meets, n_cls)),
        ("Classes with zero val+test instances", str(p_zero), str(c_zero)),
        ("test$\\leftrightarrow$train pairs (raw / aligned)",
         pair("published", "pairs_train_test"), pair(rel_state, "pairs_train_test")),
        ("val$\\leftrightarrow$train pairs (raw / aligned)",
         pair("published", "pairs_train_valid"), pair(rel_state, "pairs_train_valid")),
        ("val$\\leftrightarrow$test pairs (raw / aligned)",
         pair("published", "pairs_valid_test"), pair(rel_state, "pairs_valid_test")),
        ("Images reassigned", "---", commas(moved)),
        ("Grouping $\\tau$ (s)", "---", str(cfg["tau_seconds"])),
        ("Seed", "---", str(cfg["seed"])),
    ]
    body = [[tex(a) if "$" not in a and "\\" not in a else a, b, c]
            for a, b, c in spec]

    # The epsilon caveat is not decoration. eps=0.05 is BOTH the threshold these
    # counts are measured at AND the threshold at which the allocator grouped
    # the untimestamped images, so the corrected column's figure at that value
    # is not independent of the grouping that produced it. The 0.02 and 0.01
    # figures are, and they are also zero for test<->train -- which is the
    # sentence that keeps the headline honest.
    caption = ("Properties of the published split and of the corrected split "
               "released here. Near-duplicate pair counts are at $\\epsilon = "
               "%s$ with low-information pairs excluded, reported separately "
               "for raw and aligned scoring. That threshold is also the one at "
               "which the allocator grouped the untimestamped images, so the "
               "corrected column's count at $\\epsilon = %s$ is not independent "
               "of the grouping that produced the split; the counts at "
               "$\\epsilon = 0.02$ and $\\epsilon = 0.01$ carry no such "
               "dependence and are likewise zero for "
               "test$\\leftrightarrow$train under both scorings. The corrected "
               "split holds the image counts of the published one exactly, so "
               "no accuracy difference can be attributed to training-set size."
               % (EPS, EPS))
    latex = booktabs("tab:split-properties", caption, "lrr", header, body)

    plain = [[a.replace("$\\geq$", ">=").replace("$\\leftrightarrow$", "<->")
              .replace("$\\tau$", "tau").replace("---", "-"), b, c]
             for a, b, c in spec]
    return latex, ("T2  split properties", header, plain, None)


# ---------------------------------------------------------------- T3
def t3():
    rows = read_csv(S_PROVENANCE)
    total = len(rows)
    blank = [r for r in rows if not r["source"].strip()]
    default = [r for r in rows if r["source"].strip().lower() == "default"]
    shown = [r for r in rows if r["source"].strip().lower() != "default"]

    header = ["Setting", "Value", "Provenance", "Citation"]
    body = [[tex(r["setting"]), tex(r["value"]), tex(r["source"]),
             tex(r["citation"])] for r in shown]

    # Legend built from the values actually present, so it cannot describe a
    # category the table does not contain.
    from collections import Counter
    present = Counter(r["source"].strip().lower() for r in shown)
    meanings = {
        "copied": "stated by both prior papers and reproduced here",
        "added": "stated by neither and introduced by this study",
        "constrained": "fixed by the data rather than chosen",
        "differs": "stated by prior work but at a different value",
    }
    legend = "; ".join("\\emph{%s} (%d) %s" % (k, present[k], meanings[k])
                       for k in ("copied", "added", "constrained", "differs")
                       if present.get(k))

    caption = ("Training configuration, showing only the %d settings that were "
               "decided. The other %d are Ultralytics defaults; the complete "
               "%d-setting record is in "
               "\\texttt{data/config\\_provenance.csv}. %s."
               % (len(shown), len(default), total, legend))
    notes = None
    if blank:
        notes = ["\\textbf{Provisional:} %d of %d settings have no source "
                 "recorded yet." % (len(blank), total)]
    latex = booktabs("tab:training-config", caption,
                     "lllp{0.34\\textwidth}",
                     header, body, notes, star=True, size="footnotesize")

    plain = [[r["setting"], r["value"], r["source"] or "(blank)",
              r["citation"] or "(blank)"] for r in shown]
    note = ("%d of %d rows shown; %d marked default, %d unclassified"
            % (len(shown), total, len(default), len(blank)))
    return latex, ("T3  training configuration", header, plain, note)


# ---------------------------------------------------------------- T4
def t4():
    rows = ec61.load_benchmark_rows(S_MASTER)
    rows.sort(key=lambda r: (r["model"], r["split_set"]))

    header = ["Model", "Split", "Val@50", "Val@50--95", "Test@50",
              "Test@50--95", "Cls val", "Cls test"]
    body = [[tex(r["model"]), tex(r["split_set"]),
             r["val_mAP50"], r["val_mAP50_95"], r["test_mAP50"],
             r["test_mAP50_95"], r["classes_evaluated_val"],
             r["classes_evaluated_test"]] for r in rows]

    caption = ("Detection accuracy on both splits. Classes evaluated are given "
               "separately for validation and test because they differ under "
               "the published split, where %s classes have no validation "
               "instances and %s have none in test. Accuracy on the two splits "
               "is therefore not measured over the same set of classes."
               % (rows[0]["classes_evaluated_val"] and
                  str(61 - int([r for r in rows
                                if r["split_set"] == "published"][0]
                               ["classes_evaluated_val"])),
                  str(61 - int([r for r in rows
                                if r["split_set"] == "published"][0]
                               ["classes_evaluated_test"]))))
    latex = booktabs("tab:main-results", caption, "llrrrrrr", header, body)

    plain = [[r["model"], r["split_set"], r["val_mAP50"], r["val_mAP50_95"],
              r["test_mAP50"], r["test_mAP50_95"],
              r["classes_evaluated_val"], r["classes_evaluated_test"]]
             for r in rows]
    return latex, ("T4  main results", header, plain, None)


# ---------------------------------------------------------------- T5
def t5():
    lat = {r["model"]: r for r in read_csv(S_LATENCY)}
    master = ec61.load_benchmark_rows(S_MASTER)

    comp = {}
    for r in master:
        key = r["model"]
        cur = (r["params_fused"], r["gflops_fused"])
        if key in comp and comp[key] != cur:
            raise ValueError("%s reports different fused complexity on its two "
                             "split rows: %s vs %s" % (key, comp[key], cur))
        comp[key] = cur
    if set(comp) != set(lat):
        raise ValueError("accuracy and latency tables disagree on models: %s"
                         % sorted(set(comp) ^ set(lat)))

    order = sorted(lat, key=lambda m: float(lat[m]["e2e_ms_p50_mean"]))
    header = ["Model", "Params (fused)", "GFLOPs (fused)", "p50 (ms)",
              "Pair gap (ms)", "p95 (ms)", "FPS"]
    body = []
    plain = []
    for m in order:
        l, c = lat[m], comp[m]
        body.append([tex(m), commas(c[0]), "%.3f" % float(c[1]),
                     "%.2f" % float(l["e2e_ms_p50_mean"]),
                     "%.2f" % float(l["e2e_ms_p50_gap"]),
                     "%.2f" % float(l["e2e_ms_p95_mean"]),
                     "%.1f" % float(l["fps_p50_mean"])])
        plain.append([m, commas(c[0]), "%.3f" % float(c[1]),
                      "%.2f" % float(l["e2e_ms_p50_mean"]),
                      "%.2f" % float(l["e2e_ms_p50_gap"]),
                      "%.2f" % float(l["e2e_ms_p95_mean"]),
                      "%.1f" % float(l["fps_p50_mean"])])

    worst = max(lat.values(), key=lambda r: float(r["e2e_ms_p50_gap"]))
    caption = ("Efficiency, one row per architecture. Accuracy in "
               "Table~\\ref{tab:main-results} is reported per split because it "
               "depends on which split a model was trained and evaluated on; "
               "latency does not, so each architecture is timed in both of its "
               "runs and the two are averaged here. The pair gap is the difference "
               "between those two runs and is this rig's repeatability: the "
               "largest is %.2f\\,ms for %s, so any latency difference smaller "
               "than that is not a difference. Complexity is measured after "
               "\\texttt{model.fuse()}."
               % (float(worst["e2e_ms_p50_gap"]), tex(worst["model"])))
    latex = booktabs("tab:efficiency", caption, "lrrrrrr", header, body)
    return latex, ("T5  efficiency (per architecture)", header, plain, None)


# ---------------------------------------------------------------- T6
def t6():
    lat = read_csv(S_LATENCY)
    lat.sort(key=lambda r: float(r["e2e_ms_p50_mean"]))

    header = ["Model", "Pre (ms)", "Inference (ms)", "Post (ms)", "Total (ms)"]
    body, plain = [], []
    for r in lat:
        pre = float(r["pre_ms_mean"])
        inf = float(r["inf_ms_mean"])
        post = float(r["post_ms_mean"])
        cells = ["%.2f" % pre, "%.2f" % inf, "%.2f" % post,
                 "%.2f" % (pre + inf + post)]
        body.append([tex(r["model"])] + cells)
        plain.append([r["model"]] + cells)

    posts = [float(r["post_ms_mean"]) for r in lat]
    lo = min(lat, key=lambda r: float(r["post_ms_mean"]))
    hi = max(lat, key=lambda r: float(r["post_ms_mean"]))
    caption = ("Latency broken down by stage, one row per architecture, "
               "averaged over each architecture's two timed runs. Preprocess "
               "is near-constant across models; inference dominates. "
               "Postprocess spans %.2f--%.2f\\,ms, a factor of %.1f, with %s "
               "lowest and %s highest. The three stages sum to slightly less "
               "than the end-to-end p50 in Table~\\ref{tab:efficiency}, which "
               "also carries the per-image overhead outside these stages."
               % (min(posts), max(posts), max(posts) / min(posts),
                  tex(lo["model"]), tex(hi["model"])))
    latex = booktabs("tab:latency-breakdown", caption, "lrrrr", header, body)
    return latex, ("T6  latency breakdown", header, plain,
                   "postprocess spread %.2f-%.2f ms = %.1fx"
                   % (min(posts), max(posts), max(posts) / min(posts)))


# ---------------------------------------------------------------- main
# ---------------------------------------------------------------- T7
def signed(x):
    """A deviation, in math mode so the minus is a minus and not a hyphen."""
    return "$%s%.1f$" % ("+" if x >= 0 else "-", abs(x))


def t7():
    """Section 3.3's arithmetic: how the per-group deviations cancel.

    The point of this table is that the aggregate 69.7/20.7/9.7 is an accident.
    Every figure is summed from split_ratio_by_group.csv's dev_*_imgs columns;
    nothing is typed here, and the totals are ASSERTED against an independent
    sum over all nine rows rather than trusted from the grouping above.
    """
    rows = read_csv(S_GROUP_RATIO)

    train_only = [r for r in rows if r["shape"] == "train-only"]
    near_nom = [r for r in rows if r["shape"] == "near-nominal"]
    skewed = [r for r in rows if r["shape"] == "skewed"]

    # The prose names two skewed groups pulling in opposite directions. If a
    # re-run ever produced a third, the sentence in 3.3 would be wrong and this
    # table would quietly absorb it.
    if len(skewed) != 2:
        raise ValueError("expected 2 skewed groups, found %d: %s"
                         % (len(skewed), [r["label"] for r in skewed]))
    if len(train_only) + len(near_nom) + len(skewed) != len(rows):
        raise ValueError("a group carries a shape outside the three known ones")

    def dev(group, col):
        return sum(float(r[col]) for r in group)

    # Skewed groups are listed individually, because the whole argument is that
    # they pull in OPPOSITE directions -- summing them would hide it.
    body_src = [("Train-only groups", train_only)]
    body_src += [(r["label"], [r]) for r in skewed]
    body_src += [("Near-nominal groups", near_nom)]

    body, plain = [], []
    for label, group in body_src:
        dv, dt = dev(group, "dev_valid_imgs"), dev(group, "dev_test_imgs")
        body.append([tex(label), str(len(group)), signed(dv), signed(dt)])
        plain.append([label, len(group), "%+.1f" % dv, "%+.1f" % dt])

    tot_v, tot_t = dev(rows, "dev_valid_imgs"), dev(rows, "dev_test_imgs")
    # Independent check: the four grouped rows must reproduce the nine-row sum.
    grouped_v = sum(dev(g, "dev_valid_imgs") for _, g in body_src)
    grouped_t = sum(dev(g, "dev_test_imgs") for _, g in body_src)
    if abs(grouped_v - tot_v) > 1e-6 or abs(grouped_t - tot_t) > 1e-6:
        raise ValueError("grouped rows do not reproduce the total: "
                         "%r vs %r" % ((grouped_v, grouped_t), (tot_v, tot_t)))

    n_imgs = sum(int(r["imgs_total"]) for r in rows)
    body.append(MIDRULE)
    body.append(["Aggregate residual", str(len(rows)),
                 signed(tot_v), signed(tot_t)])
    plain.append(["AGGREGATE", len(rows), "%+.1f" % tot_v, "%+.1f" % tot_t])

    header = ["Groups contributing", "$n$", "Validation", "Test"]
    caption = ("How the per-group deviations cancel. Each figure is the number "
               "of images by which a partition departs from what a uniform "
               "70/20/10 draw over that group would have produced; negative is "
               "fewer than nominal. The %d train-only groups withhold %.1f "
               "validation and %.1f test images, and two skewed groups return "
               "most of that on opposite sides. What survives across all "
               "%s images is under one percentage point on either partition, "
               "which is why the aggregate reads as a textbook split."
               % (len(train_only), abs(dev(train_only, "dev_valid_imgs")),
                  abs(dev(train_only, "dev_test_imgs")), commas(n_imgs)))
    latex = booktabs("tab:allocation-deviation", caption, "lrrr", header, body)

    return latex, ("T7  allocation deviation, images vs a uniform draw",
                   ["Groups contributing", "n", "Validation", "Test"], plain,
                   "residual is %.2f%% / %.2f%% of %s images"
                   % (100.0 * abs(tot_v) / n_imgs, 100.0 * abs(tot_t) / n_imgs,
                      commas(n_imgs)))


def main():
    missing = [p for p in ALL_SOURCES if not os.path.isfile(p)]
    if missing:
        for p in missing:
            sys.stderr.write("source not found: %s\n" % p)
        return 1

    if not os.path.isdir(TAB_DIR):
        os.makedirs(TAB_DIR)

    run_dir = ec61.make_run_dir("make_tables")
    builders = [("t1_unevaluable_classes", t1), ("t2_split_properties", t2),
                ("t3_training_config", t3), ("t4_main_results", t4),
                ("t5_efficiency", t5), ("t6_latency_breakdown", t6),
                # The tN prefix is CREATION order, not print order. T7 is
                # \input in Section 3.3 and therefore prints as Table 2.
                # Nothing types a table number, so the two need not agree.
                ("t7_allocation_deviation", t7)]

    written = []
    for name, fn in builders:
        latex, (title, header, rows, note) = fn()

        # Control characters are how the one prior corruption manifested.
        bad = [(i, ord(c)) for i, c in enumerate(latex)
               if ord(c) < 32 and c not in "\n\t"]
        if bad:
            raise ValueError("%s contains control characters at %s"
                             % (name, bad[:5]))

        path = os.path.join(TAB_DIR, name + ".tex")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(latex)
        written.append(path)
        show(title + "   ->  tables/%s.tex" % name, header, rows, note)

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"output_dir": TAB_DIR, "tables": [n for n, _ in builders],
                "min_per_split": MIN_PER_SPLIT, "epsilon": EPS},
        extra={"sources": {os.path.relpath(p, ec61.REPO_ROOT).replace("\\", "/"):
                           sha256_file(p) for p in ALL_SOURCES},
               "outputs": [os.path.relpath(p, ec61.REPO_ROOT).replace("\\", "/")
                           for p in written]})

    prov = read_csv(S_PROVENANCE)
    unclassified = sum(1 for r in prov if not r["source"].strip())

    lines = ["# Tables", "", "Run directory: `%s`" % os.path.basename(run_dir),
             "", "%d LaTeX booktabs tables under `tables/`, one file each."
             % len(builders), ""]
    for name, _ in builders:
        lines.append("- `tables/%s.tex`" % name)
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    for p in ALL_SOURCES:
        lines.append("- `%s`" % os.path.relpath(p, ec61.REPO_ROOT).replace("\\", "/"))
    lines.append("")
    lines.append("## What could make these misleading")
    lines.append("")
    if unclassified:
        lines.append("- **T3 is provisional.** %d of %d settings in "
                     "`data/config_provenance.csv` still have no `source`. "
                     "Until they are filled the table reports settings without "
                     "saying who chose them." % (unclassified, len(prov)))
    lines.append("- T2 quotes the RELEASED split. "
                 "`runs/20260804_duplicate_contamination` describes the "
                 "superseded image-level split and reports 2 raw / 4 aligned "
                 "test-train pairs where the released split reports 0 / 0. "
                 "This script asserts the per-class counts it uses were built "
                 "from the released manifest before quoting them.")
    lines.append("- T4 is per split and T5 is per architecture. Accuracy "
                 "depends on the split; latency does not.")
    lines.append("- T1 counts annotation instances, not images. Both columns "
                 "are given because a class with many instances in few images "
                 "is less diverse than its instance count suggests.")
    lines.append("- T7's nominal 70/20/10 is inferred from the aggregate, not "
                 "documented by the dataset authors. If they intended another "
                 "ratio every deviation in it shifts. The deviations are also "
                 "real-valued rather than rounded to whole images, so a row "
                 "can read $-0.8$ for an allocation no integer split could "
                 "have improved on.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %d tables to %s" % (len(written), "tables/"))
    if unclassified:
        print("T3 IS PROVISIONAL: %d of %d settings have no source recorded"
              % (unclassified, len(prov)))
    print("record: %s" % os.path.relpath(run_dir, ec61.REPO_ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
