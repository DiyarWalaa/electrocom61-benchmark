"""
duplicate_contamination_addendum.py -- ADDENDUM to runs/20260803_corrected_split_02

WHY THIS RUN EXISTS

The Stage 3 run reported two different things under words that blurred into
each other. They are not the same measurement and must never be summed,
averaged, or reported as one number:

  TEMPORAL ADJACENCY        two images were captured close together in time.
                            Measured by burst clustering over filename
                            timestamps (burst_clusters.py). Says NOTHING about
                            whether the two images look alike.

  NEAR-DUPLICATE            two images show the same scene, judged by the
  CONTAMINATION             geometry of their annotations (scene_signature.py).
                            Says nothing about when they were taken.

Calling the published split "already leaked" on the strength of the temporal
metric contradicted Stage 1, which measured the published split on the
near-duplicate axis and found ZERO test images with a train twin at every
epsilon once low-information pairs were excluded. Both findings are correct.
They are about different things. This run reports the near-duplicate axis only,
for both splits, so the two can be quoted side by side without collision.

THE UNIT ERROR THIS RUN ALSO FIXES

"The published split had 0 near-duplicate pairs" is true for TEST<->TRAIN and
only for test<->train. Stage 1's own table shows valid<->train twins at
epsilon 0.05 (1 under raw scoring, 3 under aligned). A before/after comparison
that put "0" against a corrected-split figure counting ANY cross-split pair
would be comparing different units and would overstate the damage.

So every figure here is broken out three ways -- test<->train, valid<->train,
valid<->test -- for both splits, under both scorings, at every epsilon.

ONE SCORING PASS, TWO CLASSIFICATIONS

Each candidate pair is scored exactly once and then classified under the
published assignment and again under the corrected one. The two states
therefore share the same buckets, the same pairs and the same scorer by
construction. Any difference between them is a difference in split membership
and cannot be an artefact of measuring twice.

RECONCILIATION IS PART OF THE RESULT

The published-split figures must reproduce runs/20260802_scene_signature.
Those values are asserted below and compared. If they do not match, this run
is wrong and says so rather than quietly publishing a second set of numbers
that disagrees with the first.

Run with no arguments:

    python scripts/duplicate_contamination_addendum.py

Writes runs/<YYYYMMDD>_duplicate_contamination/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import scene_signature  # noqa: E402


# The corrected assignment being evaluated. Named explicitly: this addendum
# belongs to that specific run and to no other.
MANIFEST = os.path.join(
    ec61.RUNS_DIR, "20260803_corrected_split_02", "split_manifest.csv")

# Stage 1's published-split figures at excl_low_info=True, which this run must
# reproduce. Keyed (scoring, epsilon) -> (n_pairs, test_w_train, valid_w_train).
# Transcribed from runs/20260802_scene_signature/summary.md.
STAGE1_EXPECTED = {
    ("raw", 0.01): (1, 0, 0),
    ("raw", 0.02): (4, 0, 0),
    ("raw", 0.05): (26, 0, 1),
    ("aligned", 0.01): (3, 0, 0),
    ("aligned", 0.02): (13, 0, 0),
    ("aligned", 0.05): (85, 0, 3),
}

SCORINGS = ("raw", "aligned")

# The three cross-split relationships, named once so no table invents its own
# ordering or spelling.
CROSS_KINDS = (("train", "test"), ("train", "valid"), ("valid", "test"))


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def load_manifest(path):
    import csv
    assignment = {}
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            assignment[row["image_name"].strip()] = row["split"].strip()
    return assignment


def classify(scored, assignment, scoring, eps, excl_low_info):
    """Count cross-split near-duplicates under one assignment.

    Returns a dict with the three-way breakdown plus the image-level units
    Stage 1 reported, so the two runs can be compared directly.
    """
    idx = 2 if scoring == "raw" else 3
    n_pairs_total = 0          # all same-scene pairs, cross-split or not
    kind_counts = {k: 0 for k in CROSS_KINDS}
    n_cross = 0
    n_untimed_cross = 0
    test_twin = set()
    valid_twin = set()

    for pair in scored:
        a, b, raw_m, ali_m, low_info, involves_untimed = pair
        if excl_low_info and low_info:
            continue
        if (raw_m if scoring == "raw" else ali_m) > eps:
            continue
        n_pairs_total += 1

        sa, sb = assignment[a], assignment[b]
        if sa == sb:
            continue
        n_cross += 1
        if involves_untimed:
            n_untimed_cross += 1
        key = tuple(sorted((sa, sb)))
        # tuple(sorted(...)) yields ('test','train'), ('train','valid'),
        # ('test','valid'); map onto the canonical names.
        for k in CROSS_KINDS:
            if tuple(sorted(k)) == key:
                kind_counts[k] += 1
                break
        # Image-level units: which test/valid images have a TRAIN twin.
        if "train" in (sa, sb):
            other = a if sa != "train" else b
            if assignment[other] == "test":
                test_twin.add(other)
            elif assignment[other] == "valid":
                valid_twin.add(other)

    return {
        "n_pairs_total": n_pairs_total,
        "n_cross": n_cross,
        "train_test": kind_counts[("train", "test")],
        "train_valid": kind_counts[("train", "valid")],
        "valid_test": kind_counts[("valid", "test")],
        "test_w_train_twin": len(test_twin),
        "valid_w_train_twin": len(valid_twin),
        "cross_involving_untimestamped": n_untimed_cross,
    }


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("duplicate_contamination")

    records = ec61.load_images()
    published = {r.filename: r.split for r in records}
    corrected = load_manifest(MANIFEST)

    # Both assignments must describe the same image set, or the two states are
    # not comparable and no amount of careful counting afterwards fixes it.
    if set(published) != set(corrected):
        sys.stderr.write(
            "manifest and dataset disagree on which images exist "
            "(%d vs %d)\n" % (len(published), len(corrected)))
        return 1

    ec61.write_config(
        run_dir,
        os.path.abspath(__file__),
        params={
            "metric": "near-duplicate contamination (label geometry)",
            "not_measured_here": "temporal adjacency (see burst_clusters.py)",
            "epsilons": list(scene_signature.EPSILONS),
            "max_bucket": scene_signature.MAX_BUCKET,
            "low_info_box_count": scene_signature.LOW_INFO_BOX_COUNT,
            "scorings": list(SCORINGS),
            "manifest": MANIFEST,
        },
        extra={
            "addendum_to": "runs/20260803_corrected_split_02",
            "reconciles_against": "runs/20260802_scene_signature",
        },
    )

    boxes_by_name = {r.filename: ec61.load_boxes(r.label_path) for r in records}
    untimed = {r.filename for r in records if r.family == "counter"}

    # --- bucket and score, once ------------------------------------------
    buckets = {}
    for rec in records:
        buckets.setdefault(
            scene_signature.multiset_key(boxes_by_name[rec.filename]), []
        ).append(rec.filename)

    scored = []
    n_pairs_examined = 0
    n_buckets_compared = 0
    skipped_buckets = 0
    max_eps = max(scene_signature.EPSILONS)
    for key in sorted(buckets, key=lambda k: str(k)):
        members = sorted(buckets[key])
        if len(members) < 2:
            continue
        if len(members) > scene_signature.MAX_BUCKET:
            # Reported, never silently dropped: "did not look" must not read
            # as "found nothing".
            skipped_buckets += 1
            continue
        n_buckets_compared += 1
        n_boxes = sum(c for _cid, c in key)
        low_info = n_boxes <= scene_signature.LOW_INFO_BOX_COUNT
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                n_pairs_examined += 1
                raw = scene_signature.compare(boxes_by_name[a], boxes_by_name[b], align=False)
                ali = scene_signature.compare(boxes_by_name[a], boxes_by_name[b], align=True)
                # A pair above the loosest epsilon under BOTH scorings can
                # never be counted at any epsilon, so it is dropped here to
                # keep the table small. Nothing that could qualify is lost.
                if min(raw[0], ali[0]) > max_eps:
                    continue
                scored.append((a, b, raw[0], ali[0], low_info,
                               a in untimed or b in untimed))

    # --- classify under both assignments ----------------------------------
    rows = []
    for state, assignment in (("published", published), ("corrected", corrected)):
        for scoring in SCORINGS:
            for eps in scene_signature.EPSILONS:
                for excl in (True, False):
                    m = classify(scored, assignment, scoring, eps, excl)
                    rows.append([
                        state, scoring, eps, "yes" if excl else "no",
                        m["n_pairs_total"], m["n_cross"],
                        m["train_test"], m["train_valid"], m["valid_test"],
                        m["test_w_train_twin"], m["valid_w_train_twin"],
                        m["cross_involving_untimestamped"],
                    ])
    ec61.write_csv(
        os.path.join(run_dir, "contamination_by_state.csv"),
        ["state", "scoring", "epsilon", "excl_low_info",
         "n_pairs_total", "n_cross_split",
         "pairs_train_test", "pairs_train_valid", "pairs_valid_test",
         "test_images_w_train_twin", "valid_images_w_train_twin",
         "cross_pairs_involving_untimestamped"],
        rows,
    )

    # --- reconcile the published state against Stage 1 --------------------
    recon = []
    recon_ok = True
    for (scoring, eps), (exp_pairs, exp_test, exp_valid) in sorted(
            STAGE1_EXPECTED.items()):
        m = classify(scored, published, scoring, eps, True)
        ok = (m["n_pairs_total"] == exp_pairs
              and m["test_w_train_twin"] == exp_test
              and m["valid_w_train_twin"] == exp_valid)
        recon_ok = recon_ok and ok
        recon.append([scoring, eps,
                      exp_pairs, m["n_pairs_total"],
                      exp_test, m["test_w_train_twin"],
                      exp_valid, m["valid_w_train_twin"],
                      "yes" if ok else "**NO**"])
    ec61.write_csv(
        os.path.join(run_dir, "reconciliation_with_stage1.csv"),
        ["scoring", "epsilon",
         "stage1_n_pairs", "here_n_pairs",
         "stage1_test_w_train", "here_test_w_train",
         "stage1_valid_w_train", "here_valid_w_train", "agree"],
        recon,
    )

    # --- the pairs themselves, under the corrected split ------------------
    pair_rows = []
    for (a, b, raw_m, ali_m, low_info, involves_untimed) in scored:
        sa, sb = corrected[a], corrected[b]
        if sa == sb:
            continue
        pair_rows.append([a, sa, b, sb, "%.5f" % raw_m, "%.5f" % ali_m,
                          "yes" if low_info else "no",
                          "yes" if involves_untimed else "no",
                          published[a], published[b]])
    pair_rows.sort(key=lambda r: (min(float(r[4]), float(r[5])), r[0], r[2]))
    ec61.write_csv(
        os.path.join(run_dir, "cross_split_pairs_corrected.csv"),
        ["image_a", "split_a", "image_b", "split_b",
         "raw_max_centre_dist", "aligned_max_centre_dist",
         "low_information", "involves_untimestamped",
         "published_split_a", "published_split_b"],
        pair_rows,
    )

    # --- summary.md --------------------------------------------------------
    def row_for(state, scoring, eps, excl=True):
        for r in rows:
            if (r[0] == state and r[1] == scoring and r[2] == eps
                    and r[3] == ("yes" if excl else "no")):
                return r
        return None

    lines = []
    lines.append("# Near-duplicate contamination: published vs corrected split")
    lines.append("")
    lines.append("Addendum to `runs/20260803_corrected_split_02`. "
                 "Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("## What this measures, and what it does not")
    lines.append("")
    lines.append("**Near-duplicate contamination** -- two images show the same "
                 "scene, judged from annotation geometry. That is the only thing "
                 "measured here.")
    lines.append("")
    lines.append("**Temporal adjacency** -- two images were captured close "
                 "together in time -- is a DIFFERENT measurement, reported in "
                 "`runs/20260803_corrected_split_02/summary.md` and in "
                 "`runs/20260802_burst_clusters`. Images seconds apart need not "
                 "be near-duplicates, and near-duplicates need not be adjacent "
                 "in time. The two must never be merged into one word.")
    lines.append("")
    lines.append("## Reconciliation with Stage 1")
    lines.append("")
    lines.append("The published-split figures must reproduce "
                 "`runs/20260802_scene_signature` exactly. %s"
                 % ("They do." if recon_ok
                    else "**THEY DO NOT -- this run is unreliable.**"))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["scoring", "eps", "stage1 pairs", "here", "stage1 test~train",
         "here", "stage1 valid~train", "here", "agree"], recon))
    lines.append("")
    lines.append("## Three-way breakdown, low-information pairs excluded")
    lines.append("")
    lines.append("Cross-split near-duplicate PAIRS. `excl_low_info=True` "
                 "throughout, which is the row Stage 1 says to quote.")
    lines.append("")
    for scoring in SCORINGS:
        lines.append("**%s scoring**" % scoring)
        lines.append("")
        tbl = []
        for eps in scene_signature.EPSILONS:
            for state in ("published", "corrected"):
                r = row_for(state, scoring, eps)
                tbl.append([eps, state, r[6], r[7], r[8], r[5]])
        lines.append(_fmt_markdown_table(
            ["eps", "split", "test<->train", "valid<->train", "valid<->test",
             "all cross-split"], tbl))
        lines.append("")

    lines.append("## The corrected sentence")
    lines.append("")
    r_pub_raw = row_for("published", "raw", 0.05)
    r_cor_raw = row_for("corrected", "raw", 0.05)
    r_pub_ali = row_for("published", "aligned", 0.05)
    r_cor_ali = row_for("corrected", "aligned", 0.05)
    lines.append("The published split had **zero test<->train near-duplicate "
                 "pairs at every epsilon under both scorings** -- Stage 1's "
                 "finding, reproduced here. It did NOT have zero cross-split "
                 "pairs overall: at eps=0.05 it carries %d valid<->train pairs "
                 "under raw scoring and %d under aligned."
                 % (r_pub_raw[7], r_pub_ali[7]))
    lines.append("")
    lines.append("The corrected split at eps=0.05 carries %d test<->train and "
                 "%d valid<->train pairs under raw scoring (%d and %d under "
                 "aligned). At eps=0.02 and eps=0.01 the corresponding counts "
                 "are in the tables above."
                 % (r_cor_raw[6], r_cor_raw[7], r_cor_ali[6], r_cor_ali[7]))
    lines.append("")
    lines.append("Quote the three columns separately. A single "
                 "\"cross-split pairs\" number mixes test contamination, which "
                 "biases the headline metric, with valid contamination, which "
                 "biases model selection -- different consequences that should "
                 "not share a row.")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("- images: **%d**" % len(records))
    lines.append("- distinct class-multiset buckets: **%d**" % len(buckets))
    lines.append("- buckets compared: %d; pairs examined: %d; buckets skipped: %d"
                 % (n_buckets_compared, n_pairs_examined, skipped_buckets))
    lines.append("- pairs retained for scoring (below the loosest epsilon under "
                 "at least one scoring): %d" % len(scored))
    lines.append("- cross-split pairs under the corrected split, all epsilons "
                 "and both scorings: %d" % len(pair_rows))
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- The method UNDER-detects by construction. Pairs are only "
                 "considered when their class multisets match exactly, so one "
                 "occluded component in one frame makes a genuine duplicate "
                 "invisible. Every count here is a floor.")
    lines.append("- Annotation geometry is a proxy for visual similarity. Two "
                 "different scenes laid out identically score as duplicates; "
                 "the same scene re-annotated differently does not.")
    lines.append("- `low_information` pairs (<= %d boxes) are excluded from the "
                 "headline because a centre match is cheap to achieve by chance "
                 "with few boxes. They are still in the CSV with excl_low_info=no."
                 % scene_signature.LOW_INFO_BOX_COUNT)
    lines.append("- This says nothing about whether the corrected split is a "
                 "good split. It prices ONE axis of cost.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    print("  reconciles with Stage 1: %s" % ("YES" if recon_ok else "NO"))
    for scoring in SCORINGS:
        for eps in scene_signature.EPSILONS:
            p = row_for("published", scoring, eps)
            c = row_for("corrected", scoring, eps)
            print("  %-7s eps=%.2f  published t<->tr=%d v<->tr=%d v<->te=%d  |  "
                  "corrected t<->tr=%d v<->tr=%d v<->te=%d"
                  % (scoring, eps, p[6], p[7], p[8], c[6], c[7], c[8]))
    return 0 if recon_ok else 1


if __name__ == "__main__":
    sys.exit(main())
