"""
split_ratio_by_group.py -- how each capture session was divided, session by session

F2 shows three capture groups that never reach valid or test. This looks at the
same table one level down: what fraction of EACH group went to train, valid and
test, and how far that is from the uniform 70/20/10 the dataset appears to use
overall.

WHY THIS IS WORTH SEPARATING FROM THE TRAIN-ONLY FINDING

The aggregate split is 1478/438/205 of 2121, which is 69.7/20.6/9.7 -- to the
eye, a textbook 70/20/10. That aggregate is what a reader sees quoted in the
dataset's own documentation, and it is the thing this script is designed to
undermine: a dataset can hit 70/20/10 exactly in total while no individual
session is anywhere near it. The three all-train groups are the loudest case,
but they are not the only one, and a split that was assigned per-session rather
than per-image would show exactly this signature.

WHAT "EXPECTED" MEANS HERE

For each group, the count a uniform 70/20/10 draw over that group's images
would have produced -- total x 0.70, x 0.20, x 0.10. Left as a real number
rather than rounded to whole images: rounding would introduce a residue of up
to one image per cell that has nothing to do with the finding, and the
deviations being measured are tens of images wide.

Deviation is reported two ways. In IMAGES it says how many files sit on the
wrong side. In PERCENTAGE POINTS it makes groups of different sizes
comparable -- 17 Apr has 54 images and 20 Feb has 486, and only the points
figure lets them be read against each other.

This script draws nothing and changes no figure. It exists so the numbers can
be looked at before deciding whether they become a panel, a table, or a
sentence.

Source: runs/20260802_class_date_provenance/date_split_summary.csv
        (committed; no dependency on the gitignored dataset)

Run with no arguments:

    python scripts/split_ratio_by_group.py

Writes runs/<YYYYMMDD>_split_ratio_by_group/.
"""

import csv
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


SOURCE = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                      "date_split_summary.csv")

# The nominal ratio the dataset's aggregate matches.
NOMINAL = {"train": 0.70, "valid": 0.20, "test": 0.10}

# Two tolerances, because percentage points are the wrong instrument for a
# small group and images are the wrong instrument for a large one.
#
# NEAR_PP: every share within this many percentage points of nominal.
# NEAR_IMGS: every cell within this many IMAGES of the uniform draw.
#
# The second is the one that matters for classification here. 17 Apr holds 54
# images, so a single file moves its test share by 1.9 points -- it is scored
# "skewed" on points while sitting under one image from a perfect allocation,
# which is as close as integer arithmetic permits. Judging small sessions on
# points punishes them for rounding they cannot avoid. Both are reported so the
# disagreement is visible rather than settled silently.
NEAR_PP = 1.0
NEAR_IMGS = 1.5

UNTIMESTAMPED_KEY = "<untimestamped:counter>"

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def pretty(key):
    if len(key) == 8 and key.isdigit():
        return "%d %s %s" % (int(key[6:8]), _MONTHS[int(key[4:6]) - 1], key[:4])
    return "iPhone (no timestamp)" if key == UNTIMESTAMPED_KEY else key


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def main():
    if not os.path.isfile(SOURCE):
        sys.stderr.write("source not found: %s\n" % SOURCE)
        return 1

    run_dir = ec61.make_run_dir("split_ratio_by_group")

    with open(SOURCE, "r", newline="", encoding="utf-8-sig") as fh:
        raw = list(csv.DictReader(fh))

    groups = []
    for r in raw:
        key = r["capture_date"]
        counts = {"train": int(r["imgs_train"]), "valid": int(r["imgs_valid"]),
                  "test": int(r["imgs_test"])}
        total = int(r["imgs_total"])
        if sum(counts.values()) != total:
            raise ValueError("imgs_total disagrees with the parts for %s" % key)

        pct = {s: 100.0 * counts[s] / total for s in counts}
        exp = {s: total * NOMINAL[s] for s in counts}
        dev_img = {s: counts[s] - exp[s] for s in counts}
        dev_pp = {s: pct[s] - 100.0 * NOMINAL[s] for s in counts}
        worst = max(abs(dev_pp[s]) for s in dev_pp)

        worst_img = max(abs(dev_img[s]) for s in dev_img)

        # Classification is by IMAGES; the points version is carried alongside
        # so a reader can see where the two disagree.
        if counts["valid"] == 0 and counts["test"] == 0:
            shape = "train-only"
        elif worst_img <= NEAR_IMGS:
            shape = "near-nominal"
        else:
            shape = "skewed"

        if counts["valid"] == 0 and counts["test"] == 0:
            shape_pp = "train-only"
        elif worst <= NEAR_PP:
            shape_pp = "near-nominal"
        else:
            shape_pp = "skewed"

        groups.append({
            "key": key, "label": pretty(key), "total": total,
            "counts": counts, "pct": pct, "exp": exp,
            "dev_img": dev_img, "dev_pp": dev_pp,
            "worst_pp": worst, "worst_img": worst_img,
            "shape": shape, "shape_pp": shape_pp,
        })

    groups.sort(key=lambda g: (g["key"] == UNTIMESTAMPED_KEY, g["key"]))

    tot = {s: sum(g["counts"][s] for g in groups) for s in NOMINAL}
    tot_all = sum(g["total"] for g in groups)
    tot_pct = {s: 100.0 * tot[s] / tot_all for s in tot}

    ec61.write_csv(
        os.path.join(run_dir, "split_ratio_by_group.csv"),
        ["capture_group", "label", "imgs_total",
         "imgs_train", "imgs_valid", "imgs_test",
         "pct_train", "pct_valid", "pct_test",
         "expected_train_70", "expected_valid_20", "expected_test_10",
         "dev_train_imgs", "dev_valid_imgs", "dev_test_imgs",
         "dev_train_pp", "dev_valid_pp", "dev_test_pp",
         "max_abs_dev_pp", "max_abs_dev_imgs", "shape", "shape_by_pp"],
        [[g["key"], g["label"], g["total"],
          g["counts"]["train"], g["counts"]["valid"], g["counts"]["test"],
          round(g["pct"]["train"], 2), round(g["pct"]["valid"], 2),
          round(g["pct"]["test"], 2),
          round(g["exp"]["train"], 1), round(g["exp"]["valid"], 1),
          round(g["exp"]["test"], 1),
          round(g["dev_img"]["train"], 1), round(g["dev_img"]["valid"], 1),
          round(g["dev_img"]["test"], 1),
          round(g["dev_pp"]["train"], 2), round(g["dev_pp"]["valid"], 2),
          round(g["dev_pp"]["test"], 2),
          round(g["worst_pp"], 2), round(g["worst_img"], 2),
          g["shape"], g["shape_pp"]]
         for g in groups])

    by_shape = {}
    for g in groups:
        by_shape.setdefault(g["shape"], []).append(g["label"])

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"source": SOURCE, "nominal": NOMINAL,
                "near_nominal_tolerance_pp": NEAR_PP,
                "expected_rounding": "none; real-valued total x ratio"},
        extra={"source_sha256": sha256_file(SOURCE),
               "aggregate_pct": {s: round(tot_pct[s], 2) for s in tot_pct},
               "shape_counts": {k: len(v) for k, v in by_shape.items()},
               "shape_members": by_shape})

    # ---- print ------------------------------------------------------------
    print("Per-capture-group split ratios, published split")
    print("source: %s" % os.path.relpath(SOURCE, ec61.REPO_ROOT).replace("\\", "/"))
    print()
    print("  %-22s %6s  %18s  %22s %8s  %s"
          % ("group", "images", "actual %  tr/va/te",
             "deviation pp  tr/va/te", "worst_img", "shape"))
    print("  " + "-" * 102)
    for g in groups:
        print("  %-22s %6d  %6.1f %5.1f %5.1f  %7.1f %7.1f %7.1f %8.1f  %s"
              % (g["label"], g["total"],
                 g["pct"]["train"], g["pct"]["valid"], g["pct"]["test"],
                 g["dev_pp"]["train"], g["dev_pp"]["valid"], g["dev_pp"]["test"],
                 g["worst_img"], g["shape"]))
    print("  " + "-" * 102)
    print("  %-22s %6d  %6.1f %5.1f %5.1f   <- aggregate, near-nominal"
          % ("ALL GROUPS", tot_all, tot_pct["train"], tot_pct["valid"],
             tot_pct["test"]))
    print()
    print("  deviation in IMAGES (actual minus a uniform 70/20/10 draw)")
    print("  %-22s %8s %8s %8s" % ("group", "train", "valid", "test"))
    print("  " + "-" * 52)
    for g in groups:
        print("  %-22s %8.1f %8.1f %8.1f"
              % (g["label"], g["dev_img"]["train"], g["dev_img"]["valid"],
                 g["dev_img"]["test"]))
    print()
    for shape in ("near-nominal", "train-only", "skewed"):
        if shape in by_shape:
            print("  %-13s %d: %s" % (shape, len(by_shape[shape]),
                                      ", ".join(by_shape[shape])))
    disagree = [g for g in groups if g["shape"] != g["shape_pp"]]
    if disagree:
        print()
        print("  classified differently by percentage points (small groups):")
        for g in disagree:
            print("    %-22s by images=%-13s by points=%s  (%d images, "
                  "1 image = %.1f pp)"
                  % (g["label"], g["shape"], g["shape_pp"], g["total"],
                     100.0 / g["total"]))
    print()
    print("wrote %s" % os.path.relpath(run_dir, ec61.REPO_ROOT).replace("\\", "/"))

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Split ratio by capture group")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("Source: `%s`"
                 % os.path.relpath(SOURCE, ec61.REPO_ROOT).replace("\\", "/"))
    lines.append("")
    lines.append("The aggregate split is **%.1f / %.1f / %.1f** over %d images "
                 "— to the eye a textbook 70/20/10. Per capture group it is "
                 "nothing of the sort."
                 % (tot_pct["train"], tot_pct["valid"], tot_pct["test"], tot_all))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["group", "images", "train %", "valid %", "test %",
         "dev train pp", "dev valid pp", "dev test pp", "shape"],
        [[g["label"], g["total"],
          "%.1f" % g["pct"]["train"], "%.1f" % g["pct"]["valid"],
          "%.1f" % g["pct"]["test"],
          "%+.1f" % g["dev_pp"]["train"], "%+.1f" % g["dev_pp"]["valid"],
          "%+.1f" % g["dev_pp"]["test"], g["shape"]] for g in groups]))
    lines.append("")
    lines.append("## Deviation in images")
    lines.append("")
    lines.append("Actual minus what a uniform 70/20/10 draw over that group "
                 "would have produced. Not rounded to whole images: the "
                 "residue of rounding would be up to one image per cell and "
                 "the deviations here are tens wide.")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["group", "images", "train", "valid", "test"],
        [[g["label"], g["total"],
          "%+.1f" % g["dev_img"]["train"], "%+.1f" % g["dev_img"]["valid"],
          "%+.1f" % g["dev_img"]["test"]] for g in groups]))
    lines.append("")
    lines.append("## Shapes")
    lines.append("")
    for shape in ("near-nominal", "train-only", "skewed"):
        if shape in by_shape:
            lines.append("- **%s** (%d): %s"
                         % (shape, len(by_shape[shape]),
                            ", ".join("`%s`" % s for s in by_shape[shape])))
    lines.append("")
    lines.append("`near-nominal` means every cell is within **%.1f images** of "
                 "the uniform draw — as close as integer arithmetic permits."
                 % NEAR_IMGS)
    lines.append("")
    disagree = [g for g in groups if g["shape"] != g["shape_pp"]]
    if disagree:
        lines.append("### Where the two tolerances disagree")
        lines.append("")
        lines.append("Classifying on percentage points instead (within %.1f pp) "
                     "moves these groups, and the reason is group size rather "
                     "than composition:" % NEAR_PP)
        lines.append("")
        for g in disagree:
            lines.append("- **%s** — by images `%s`, by points `%s`. It holds "
                         "%d images, so one file is worth %.1f percentage "
                         "points; its worst cell is %.1f images from a perfect "
                         "allocation."
                         % (g["label"], g["shape"], g["shape_pp"], g["total"],
                            100.0 / g["total"], g["worst_img"]))
        lines.append("")
        lines.append("Points punish a small session for rounding it cannot "
                     "avoid, which is why the images measure is the one used "
                     "for the `shape` column.")
    lines.append("")
    exact = [g for g in groups if g["worst_img"] == 0.0]
    if exact:
        lines.append("### Exact allocations")
        lines.append("")
        for g in exact:
            lines.append("- **%s** splits %d/%d/%d of %d — exactly 70/20/10, "
                         "zero deviation in every cell."
                         % (g["label"], g["counts"]["train"],
                            g["counts"]["valid"], g["counts"]["test"],
                            g["total"]))
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- The nominal 70/20/10 is inferred from the aggregate, not "
                 "documented by the dataset authors. If they intended some "
                 "other ratio, every deviation here shifts.")
    lines.append("- Percentages over small groups are coarse: 17 Apr has 54 "
                 "images, so one image moves its test share by 1.9 points. "
                 "The images column is there to keep that visible.")
    lines.append("- Ratios are over IMAGES. A split that looks balanced by "
                 "image can still be unbalanced by annotation instance, which "
                 "is what actually feeds a detector's loss.")
    lines.append("- Shape is a label applied at one tolerance, not a test. "
                 "`near-nominal` at 1.0 pp would admit more groups at 2.0.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
