"""
class_date_provenance.py -- WHY are some classes never evaluated?

An external YOLOv9 run reported that 15 of the 61 classes have zero instances
in BOTH valid and test, and 16 are missing from valid. This script asks where
those classes' annotations actually come from, and tests one explanation:

  HYPOTHESIS
    The never-evaluated classes were only ever photographed in capture
    sessions that landed entirely in train. They are not rare -- they are
    session-confined. A random image-level split cannot separate them,
    because there was never an image of them outside those sessions.

WHY THE EXTERNAL COUNTS ARE RECOMPUTED RATHER THAN TRUSTED

The 15/16 figures come from a run against Roboflow project version 5
(reference/electrocom61-yolov9.ipynb, cell 29). The archive this study
analyses -- doi:10.17632/6scy6h8sjz.2 -- is Roboflow version 9. Those are
different exports and may differ in content, split assignment or both.

So every count here is derived from the v2 label files on disk. The externally
reported numbers are recorded in config.json as EXPECTED values and compared
against what is measured. A mismatch is reported as a finding, loudly, rather
than being smoothed over -- if v9 has 14 never-evaluated classes and not 15,
that is a fact about the dataset revision and belongs in the paper.

THE HYPOTHESIS IS TESTED PER CLASS, NOT ASSERTED IN AGGREGATE

Listing the capture dates of the never-evaluated classes would produce a table
consistent with the hypothesis without ever testing it. The actual test is
whether each class's dates are train-only. Every never-evaluated class is
therefore given a verdict:

  session_confined -- every date this class appears on is a date whose images
                      are ALL in train (or the untimestamped counter images).
                      Consistent with the hypothesis.
  rarity           -- this class appears on at least one date that DOES have
                      valid or test images, yet no instance of it was sampled
                      into valid or test. The hypothesis does not explain this
                      class; scarcity does.
  mixed            -- both kinds of date present.

A single `rarity` verdict does not refute the hypothesis for the others, and a
table of all-`session_confined` verdicts does not prove a causal claim. What
the verdict column does is make the distinction visible instead of assumed.

SPLIT COMES FROM THE DIRECTORY, NOT FROM THE CSV

runs/20260801_csv_coverage found 600 joined rows whose DATA_TYPE disagrees
with the directory the image actually sits in. Directory membership is what a
training run sees, so directory membership is what defines the split here.

TWO UNITS ARE COUNTED, DELIBERATELY

  instances -- annotation rows (boxes). What a detector's per-class AP is
               computed over.
  images    -- distinct images containing at least one box of the class.

Four instances inside a single image is a far weaker evaluation basis than
four instances across four images, and reporting only one of the two numbers
would hide that.

Run with no arguments:

    python scripts/class_date_provenance.py

Writes runs/<YYYYMMDD>_class_date_provenance/ (auto-suffixed, never overwriting).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# Externally reported figures being checked. These are INPUTS to a comparison,
# never substitutes for measurement; they are echoed into config.json so the
# claim being tested is recorded alongside the result.
EXPECTED_NEVER_EVALUATED = 15   # zero instances in BOTH valid and test
EXPECTED_MISSING_VALID = 16     # zero instances in valid
EXPECTED_TRAIN_ONLY_DATES = ("20240219", "20240220")
EXPECTED_UNTIMESTAMPED_IMAGES = 189

# Bucket label for images whose filenames encode no capture time (the `counter`
# family, IMG_5126 etc.). They cannot be placed on a timeline, so they are held
# in a named bucket rather than dropped -- a dropped bucket would make a class
# that lives entirely in those images look like it has no provenance at all.
UNTIMESTAMPED = "<untimestamped:counter>"

# Bucket label for a filename that matched no known family at all.
UNPARSED = "<unparsed-filename>"

# Test-instance thresholds reported as a cumulative histogram. The question
# asked was "how many classes have fewer than 5", but answering only at 5 would
# make an arbitrary cut look principled, so the neighbouring cuts are shown too.
TEST_COUNT_THRESHOLDS = (1, 2, 3, 4, 5, 10, 20)


def _fmt_markdown_table(header, rows):
    """Render a list-of-lists as a GitHub-flavoured markdown table."""
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def load_class_names(data_yaml):
    """Extract `nc` and `names` from the dataset's data.yaml.

    Deliberately NOT a general YAML parser -- this project is standard library
    only. The two fields needed have a rigid shape in a Roboflow export:

        nc: 61
        names: ['1-5-Volt-Battery', '3-3-Volt-Battery', ...]

    The names list is captured from `names:` up to the first closing bracket.
    That is safe here because no class name contains ']'; if a future export
    breaks that assumption the literal parse below fails loudly rather than
    returning a truncated list.

    Returns (names_list, declared_nc).
    """
    with open(data_yaml, "r", encoding="utf-8") as fh:
        text = fh.read()

    m_nc = re.search(r"^nc:\s*(\d+)\s*$", text, re.MULTILINE)
    if m_nc is None:
        raise ValueError("could not find `nc:` in %s" % data_yaml)
    declared_nc = int(m_nc.group(1))

    # DOTALL so a names list that has been wrapped across lines still matches.
    m_names = re.search(r"^names:\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL)
    if m_names is None:
        raise ValueError("could not find `names:` in %s" % data_yaml)

    # ast.literal_eval, not eval: the file is data, and it is parsed as data.
    import ast
    names = ast.literal_eval(m_names.group(1))
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError("`names:` in %s is not a list of strings" % data_yaml)

    if len(names) != declared_nc:
        # Not fatal -- but it must never pass silently, because every per-class
        # table downstream is indexed by position in this list.
        raise ValueError(
            "data.yaml disagrees with itself: nc=%d but %d names listed"
            % (declared_nc, len(names))
        )
    return names, declared_nc


def date_bucket(rec):
    """The capture-date bucket an image belongs to.

    Timestamped families yield their YYYYMMDD. The counter family and any
    unparsed filename yield explicit sentinel buckets so they remain visible
    in every table.
    """
    if rec.family == "counter":
        return UNTIMESTAMPED
    if rec.date_str:
        return rec.date_str
    # A timestamped family whose date failed to parse (e.g. an impossible
    # calendar date) lands here rather than being counted as a real session.
    return UNPARSED


def main():
    run_dir = ec61.make_run_dir("class_date_provenance")

    data_yaml = os.path.join(ec61.DATASET_DIR, "data.yaml")
    names, declared_nc = load_class_names(data_yaml)

    ec61.write_config(
        run_dir,
        os.path.abspath(__file__),
        params={
            "split_source": "directory on disk (NOT csv DATA_TYPE)",
            "units_counted": ["instances (boxes)", "images (distinct)"],
            "test_count_thresholds": list(TEST_COUNT_THRESHOLDS),
            "untimestamped_bucket": UNTIMESTAMPED,
        },
        extra={
            "external_claims_under_test": {
                "source": "reference/electrocom61-yolov9.ipynb (Roboflow v5)",
                "note": "this dataset is Roboflow v9; counts are recomputed, not assumed",
                "expected_never_evaluated": EXPECTED_NEVER_EVALUATED,
                "expected_missing_valid": EXPECTED_MISSING_VALID,
                "expected_train_only_dates": list(EXPECTED_TRAIN_ONLY_DATES),
                "expected_untimestamped_images": EXPECTED_UNTIMESTAMPED_IMAGES,
            },
            "declared_nc": declared_nc,
        },
    )

    records = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    n_joined, n_missing_csv = ec61.attach_metadata(records, rows_by_key)

    # ----------------------------------------------------------------------
    # Accumulate. Every counter is keyed by class id, split and date bucket so
    # that no later question requires a second pass over the label files.
    # ----------------------------------------------------------------------

    # inst[cid][split] -> number of boxes
    inst = {c: {s: 0 for s in ec61.SPLITS} for c in range(declared_nc)}
    # imgs[cid][split] -> set of filenames containing >=1 box of this class
    imgs = {c: {s: set() for s in ec61.SPLITS} for c in range(declared_nc)}
    # cls_date[cid][date][split] -> boxes of this class on this date in this split
    cls_date = {c: {} for c in range(declared_nc)}
    # date_imgs[date][split] -> number of IMAGES (not boxes) captured that date
    date_imgs = {}

    n_images_missing_label = 0
    n_boxes_total = 0
    out_of_range_ids = {}   # class id -> count, for ids not in 0..nc-1

    for rec in records:
        bucket = date_bucket(rec)
        d = date_imgs.setdefault(bucket, {s: 0 for s in ec61.SPLITS})
        d[rec.split] = d.get(rec.split, 0) + 1

        if rec.label_path is None:
            # An image with no label file contributes no instances. Counted and
            # reported, because silently treating it as "background" would
            # understate every per-class total.
            n_images_missing_label += 1
            continue

        boxes = ec61.load_boxes(rec.label_path)
        seen_here = set()   # classes already credited an image for this file
        for (cid, _cx, _cy, _w, _h) in boxes:
            n_boxes_total += 1
            if cid < 0 or cid >= declared_nc:
                # A class id outside the declared range means the labels and
                # data.yaml disagree. Recorded rather than raising, so the rest
                # of the table is still produced, but surfaced in the summary.
                out_of_range_ids[cid] = out_of_range_ids.get(cid, 0) + 1
                continue
            inst[cid][rec.split] += 1
            if cid not in seen_here:
                imgs[cid][rec.split].add(rec.filename)
                seen_here.add(cid)
            per_date = cls_date[cid].setdefault(bucket, {s: 0 for s in ec61.SPLITS})
            per_date[rec.split] += 1

    # ----------------------------------------------------------------------
    # Which dates are train-only?
    #
    # Defined on IMAGES, not on instances: a date is train-only if every image
    # captured that date sits in train/. That is the property the hypothesis is
    # about -- whether the session as a whole escaped the valid/test draw.
    # ----------------------------------------------------------------------
    train_only_dates = set()
    for bucket, per_split in date_imgs.items():
        if per_split["train"] > 0 and per_split["valid"] == 0 and per_split["test"] == 0:
            train_only_dates.add(bucket)

    # Compare against the dates the hypothesis named. Computed, not assumed.
    expected_set = set(EXPECTED_TRAIN_ONLY_DATES)
    timestamped_train_only = {b for b in train_only_dates
                              if b not in (UNTIMESTAMPED, UNPARSED)}
    train_only_matches_expected = (timestamped_train_only == expected_set)

    # ----------------------------------------------------------------------
    # Classify every class by evaluation coverage.
    # ----------------------------------------------------------------------
    never_evaluated = [c for c in range(declared_nc)
                       if inst[c]["valid"] == 0 and inst[c]["test"] == 0]
    missing_valid = [c for c in range(declared_nc) if inst[c]["valid"] == 0]
    missing_test = [c for c in range(declared_nc) if inst[c]["test"] == 0]
    absent_everywhere = [c for c in range(declared_nc)
                         if sum(inst[c][s] for s in ec61.SPLITS) == 0]

    # ----------------------------------------------------------------------
    # Per-class verdict on the hypothesis, for the never-evaluated classes.
    # ----------------------------------------------------------------------
    verdicts = {}
    for c in never_evaluated:
        dates_used = sorted(cls_date[c].keys())
        confined_dates = []     # dates that never reach valid/test
        escaping_dates = []     # dates that DO have valid/test images
        for b in dates_used:
            if b in train_only_dates or b == UNTIMESTAMPED:
                # The untimestamped bucket counts as confined only if it really
                # is train-only; checked explicitly rather than assumed.
                if b == UNTIMESTAMPED and b not in train_only_dates:
                    escaping_dates.append(b)
                else:
                    confined_dates.append(b)
            else:
                escaping_dates.append(b)

        if escaping_dates and confined_dates:
            verdict = "mixed"
        elif escaping_dates:
            verdict = "rarity"
        elif confined_dates:
            verdict = "session_confined"
        else:
            # No dates at all means no annotations anywhere -- a different
            # problem, and labelled as such rather than folded into a verdict.
            verdict = "no_annotations"
        verdicts[c] = (verdict, dates_used, confined_dates, escaping_dates)

    # ----------------------------------------------------------------------
    # Outputs
    # ----------------------------------------------------------------------

    # 1. Every class, every split, both units.
    rows = []
    for c in range(declared_nc):
        rows.append([
            c, names[c],
            inst[c]["train"], inst[c]["valid"], inst[c]["test"],
            sum(inst[c][s] for s in ec61.SPLITS),
            len(imgs[c]["train"]), len(imgs[c]["valid"]), len(imgs[c]["test"]),
        ])
    ec61.write_csv(
        os.path.join(run_dir, "class_split_counts.csv"),
        ["class_id", "class_name",
         "inst_train", "inst_valid", "inst_test", "inst_total",
         "imgs_train", "imgs_valid", "imgs_test"],
        rows,
    )

    # 2. Test-instance counts, ascending -- the "how many below 5" table.
    test_sorted = sorted(range(declared_nc), key=lambda c: (inst[c]["test"], names[c]))
    ec61.write_csv(
        os.path.join(run_dir, "test_instance_counts.csv"),
        ["rank", "class_id", "class_name", "inst_test", "imgs_test", "inst_total"],
        [[i + 1, c, names[c], inst[c]["test"], len(imgs[c]["test"]),
          sum(inst[c][s] for s in ec61.SPLITS)]
         for i, c in enumerate(test_sorted)],
    )

    # Cumulative histogram of classes below each threshold.
    threshold_rows = []
    for t in TEST_COUNT_THRESHOLDS:
        n_below = sum(1 for c in range(declared_nc) if inst[c]["test"] < t)
        threshold_rows.append([t, n_below, "%.1f%%" % (100.0 * n_below / declared_nc)])
    ec61.write_csv(
        os.path.join(run_dir, "test_count_thresholds.csv"),
        ["fewer_than", "n_classes", "pct_of_61"],
        threshold_rows,
    )

    # 3. Class x date, long format. Long rather than wide because the date set
    #    is sparse per class and a wide matrix would be mostly zeros.
    long_rows = []
    for c in range(declared_nc):
        for b in sorted(cls_date[c].keys()):
            per_split = cls_date[c][b]
            long_rows.append([
                c, names[c], b,
                per_split["train"], per_split["valid"], per_split["test"],
                sum(per_split.values()),
                "yes" if b in train_only_dates else "no",
            ])
    ec61.write_csv(
        os.path.join(run_dir, "class_by_date.csv"),
        ["class_id", "class_name", "capture_date",
         "inst_train", "inst_valid", "inst_test", "inst_total",
         "date_is_train_only"],
        long_rows,
    )

    # 4. The never-evaluated classes with their verdicts.
    ne_rows = []
    for c in never_evaluated:
        verdict, dates_used, confined, escaping = verdicts[c]
        ne_rows.append([
            c, names[c], verdict,
            inst[c]["train"], len(imgs[c]["train"]),
            len(dates_used),
            ";".join(dates_used),
            ";".join(confined),
            ";".join(escaping),
        ])
    ec61.write_csv(
        os.path.join(run_dir, "never_evaluated_classes.csv"),
        ["class_id", "class_name", "verdict",
         "inst_train", "imgs_train", "n_dates",
         "all_dates", "train_only_dates", "dates_reaching_valid_or_test"],
        ne_rows,
    )

    # 5. Every date, images and instances per split.
    date_rows = []
    for b in sorted(date_imgs.keys()):
        per_split = date_imgs[b]
        inst_here = {s: 0 for s in ec61.SPLITS}
        for c in range(declared_nc):
            if b in cls_date[c]:
                for s in ec61.SPLITS:
                    inst_here[s] += cls_date[c][b][s]
        date_rows.append([
            b,
            per_split["train"], per_split["valid"], per_split["test"],
            sum(per_split.values()),
            inst_here["train"], inst_here["valid"], inst_here["test"],
            "yes" if b in train_only_dates else "no",
        ])
    ec61.write_csv(
        os.path.join(run_dir, "date_split_summary.csv"),
        ["capture_date", "imgs_train", "imgs_valid", "imgs_test", "imgs_total",
         "inst_train", "inst_valid", "inst_test", "date_is_train_only"],
        date_rows,
    )

    # ----------------------------------------------------------------------
    # summary.md
    # ----------------------------------------------------------------------
    n_untimestamped = sum(date_imgs.get(UNTIMESTAMPED, {s: 0 for s in ec61.SPLITS}).values())
    untimestamped_splits = date_imgs.get(UNTIMESTAMPED, {s: 0 for s in ec61.SPLITS})

    verdict_counts = {}
    for c in never_evaluated:
        v = verdicts[c][0]
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    n_below_5 = sum(1 for c in range(declared_nc) if inst[c]["test"] < 5)

    lines = []
    lines.append("# Class coverage vs capture date")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("Tests whether the never-evaluated classes are **session-confined** "
                 "(only photographed on dates that landed entirely in train) or "
                 "merely **rare**.")
    lines.append("")

    lines.append("## Inputs as measured")
    lines.append("")
    lines.append("- images on disk: **%d** (train %d, valid %d, test %d)" % (
        len(records),
        sum(1 for r in records if r.split == "train"),
        sum(1 for r in records if r.split == "valid"),
        sum(1 for r in records if r.split == "test"),
    ))
    lines.append("- annotation instances parsed: **%d**" % n_boxes_total)
    lines.append("- images with no label file: **%d**" % n_images_missing_label)
    lines.append("- classes declared in data.yaml: **%d**" % declared_nc)
    lines.append("- CSV rows joined / unjoined: %d / %d" % (n_joined, n_missing_csv))
    if out_of_range_ids:
        lines.append("- **class ids outside 0..%d found in labels: %s**"
                     % (declared_nc - 1, sorted(out_of_range_ids.items())))
    lines.append("")

    lines.append("## Externally reported figures vs this dataset")
    lines.append("")
    lines.append("The 15/16 figures come from a run against Roboflow **v5**; this "
                 "archive is Roboflow **v9**. Recomputed here:")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["quantity", "externally reported", "measured here", "agree?"],
        [
            ["classes with 0 instances in valid AND test",
             EXPECTED_NEVER_EVALUATED, len(never_evaluated),
             "yes" if len(never_evaluated) == EXPECTED_NEVER_EVALUATED else "**NO**"],
            ["classes with 0 instances in valid",
             EXPECTED_MISSING_VALID, len(missing_valid),
             "yes" if len(missing_valid) == EXPECTED_MISSING_VALID else "**NO**"],
            ["untimestamped (counter) images",
             EXPECTED_UNTIMESTAMPED_IMAGES, n_untimestamped,
             "yes" if n_untimestamped == EXPECTED_UNTIMESTAMPED_IMAGES else "**NO**"],
            ["train-only capture dates",
             ", ".join(EXPECTED_TRAIN_ONLY_DATES),
             ", ".join(sorted(timestamped_train_only)) or "(none)",
             "yes" if train_only_matches_expected else "**NO**"],
        ]))
    lines.append("")
    lines.append("Classes with 0 instances in test: **%d**. "
                 "Classes absent from all three splits: **%d**."
                 % (len(missing_test), len(absent_everywhere)))
    lines.append("")

    lines.append("## The untimestamped images")
    lines.append("")
    lines.append("`%s` bucket: **%d images** (train %d, valid %d, test %d). "
                 "Train-only: **%s**."
                 % (UNTIMESTAMPED, n_untimestamped,
                    untimestamped_splits["train"], untimestamped_splits["valid"],
                    untimestamped_splits["test"],
                    "yes" if UNTIMESTAMPED in train_only_dates else "no"))
    lines.append("")
    lines.append("These carry no capture time, so they cannot be placed on the "
                 "session timeline. They are counted as a confined bucket only "
                 "if measured to be train-only.")
    lines.append("")

    lines.append("## Hypothesis verdicts")
    lines.append("")
    lines.append("For each class with zero instances in both valid and test:")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["verdict", "n classes", "meaning"],
        [
            ["session_confined", verdict_counts.get("session_confined", 0),
             "every date it appears on is train-only -- supports the hypothesis"],
            ["rarity", verdict_counts.get("rarity", 0),
             "appears on dates that DO reach valid/test -- hypothesis does not explain it"],
            ["mixed", verdict_counts.get("mixed", 0),
             "both kinds of date present"],
            ["no_annotations", verdict_counts.get("no_annotations", 0),
             "no instances anywhere in the dataset"],
        ]))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["class_id", "class_name", "verdict", "inst_train", "imgs_train", "dates"],
        [[c, names[c], verdicts[c][0], inst[c]["train"], len(imgs[c]["train"]),
          ";".join(verdicts[c][1])] for c in never_evaluated]))
    lines.append("")

    lines.append("## Test-set instance counts")
    lines.append("")
    lines.append("Classes with **fewer than 5** test instances: **%d of %d**."
                 % (n_below_5, declared_nc))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["fewer than", "n classes", "pct of 61"],
        threshold_rows))
    lines.append("")
    lines.append("Twenty lowest test counts:")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["class_id", "class_name", "inst_test", "imgs_test", "inst_total"],
        [[c, names[c], inst[c]["test"], len(imgs[c]["test"]),
          sum(inst[c][s] for s in ec61.SPLITS)] for c in test_sorted[:20]]))
    lines.append("")

    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- A `session_confined` verdict is **consistent with** the "
                 "hypothesis, not proof of it. Capture date is a proxy for "
                 "session; two unrelated shoots on one day share a bucket.")
    lines.append("- Dates come from filenames, not EXIF. If Roboflow renamed "
                 "anything the timeline inherits that error.")
    lines.append("- The `%s` bucket is one bucket covering many real sessions, "
                 "so a class confined to it is confined to *something*, but the "
                 "granularity is unknown." % UNTIMESTAMPED)
    lines.append("- Instance counts are annotation rows. Missing or wrong "
                 "annotations propagate directly; the notebook's own author "
                 "flags relabelling issues in this dataset.")
    lines.append("- `rarity` and `session_confined` are not exclusive causes. A "
                 "class can be both rare and confined; the verdict reports only "
                 "whether a non-train-only date exists for it.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # Console output mirrors the headline numbers so a run is legible without
    # opening the files.
    print("wrote %s" % run_dir)
    print("  never-evaluated classes : %d (expected %d)"
          % (len(never_evaluated), EXPECTED_NEVER_EVALUATED))
    print("  missing from valid      : %d (expected %d)"
          % (len(missing_valid), EXPECTED_MISSING_VALID))
    print("  train-only dates        : %s" % (sorted(timestamped_train_only),))
    print("  untimestamped images    : %d (expected %d)"
          % (n_untimestamped, EXPECTED_UNTIMESTAMPED_IMAGES))
    print("  verdicts                : %s" % (verdict_counts,))
    print("  classes with <5 test    : %d" % n_below_5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
