"""
consecutive_counter_pairs.py -- are sequential camera shots split apart?

THE OBSERVATION BEING QUANTIFIED

figures/split_verification_sheet.png showed three pairs of `counter`-family
images whose filename numbers are consecutive (IMG_5189/IMG_5190,
IMG_5215/IMG_5216, IMG_5268/IMG_5269) sitting on opposite sides of the released
split. Consecutive counter values come from one camera shooting in sequence, so
such a pair is very likely the same scene -- a burst in everything but name.

That was three observations from a sheet showing 24 rows. This script counts
ALL of them, exactly.

WHY THEY WERE NEVER GROUPED

These filenames encode no capture time, so burst_clusters.py cannot see them at
all. The released allocator groups them instead by scene component: images are
merged when their label geometry says "same scene" at eps=0.05. A consecutive
pair scoring just above that threshold is therefore never merged, and nothing
stops the two frames landing in different splits.

The counter number itself -- an ordering signal sitting in the filename -- is
used by neither mechanism. This script measures what that costs.

TWO KINDS OF PAIR, AND THE SECOND IS THE INTERESTING ONE

  same class multiset       a distance can be computed, and the pair was at
                            least CONSIDERED by the duplicate detector

  different class multiset  scene_signature buckets by exact class inventory,
                            so this pair was never compared at all. It has no
                            distance under this method -- not a large one, none.
                            A cross-split pair in this category is invisible to
                            every contamination number in this repository.

Reporting a single "distance" column for both would fabricate a measurement for
the second kind, so they are separated and counted separately.

THIS SCRIPT CHANGES NOTHING. It reads the released split and reports. No
manifest is written, no image is moved.

Run with no arguments:

    python scripts/consecutive_counter_pairs.py

Writes runs/<YYYYMMDD>_consecutive_counter_pairs/ (auto-suffixed).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import scene_signature  # noqa: E402


# The released split, read from the built tree so the folder each image sits in
# is the authority -- the same convention as the verification sheet.
DATASET = os.path.join(ec61.DATA_DIR, "ElectroCom-61_corrected")

REL_LABEL = {("test", "train"): "test<->train",
             ("train", "valid"): "valid<->train",
             ("test", "valid"): "valid<->test"}
RELATIONSHIPS = ("test<->train", "valid<->train", "valid<->test")


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def main():
    if not os.path.isdir(DATASET):
        sys.stderr.write("released tree not found: %s\n"
                         "Build it: python scripts/build_corrected_dataset.py\n"
                         % DATASET)
        return 1

    run_dir = ec61.make_run_dir("consecutive_counter_pairs")

    # ---- collect the counter family from the released tree ---------------
    recs = []
    for split in ec61.SPLITS:
        img_dir = os.path.join(DATASET, split, "images")
        lbl_dir = os.path.join(DATASET, split, "labels")
        for fname in sorted(os.listdir(img_dir)):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            stem = ec61.parse_stem(fname) or fname
            family, m = ec61.classify_stem(stem)
            if family != "counter":
                continue
            base = fname.rsplit(".", 1)[0]
            recs.append({
                "file": fname, "stem": stem, "split": split,
                "counter": int(m.group("counter")),
                "boxes": ec61.load_boxes(os.path.join(lbl_dir, base + ".txt")),
            })

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"dataset": DATASET,
                "family": "counter",
                "adjacency_rule": "abs(counter_a - counter_b) == 1",
                "distance": "scene_signature.compare, raw and aligned",
                "low_info_box_count": scene_signature.LOW_INFO_BOX_COUNT},
        extra={"split_read": "released burst-aware tau=15",
               "writes_manifest": False,
               "modifies_split": False})

    # A repeated counter value would make "the pair with counter n+1" ambiguous.
    by_counter = {}
    duplicates = []
    for r in recs:
        if r["counter"] in by_counter:
            duplicates.append(r["counter"])
        by_counter[r["counter"]] = r

    counters = sorted(by_counter)

    # ---- every pair differing by exactly 1 -------------------------------
    pairs = []
    for c in counters:
        if c + 1 not in by_counter:
            continue
        a, b = by_counter[c], by_counter[c + 1]
        same_multiset = (scene_signature.multiset_key(a["boxes"])
                         == scene_signature.multiset_key(b["boxes"]))
        raw = aligned = None
        if same_multiset:
            # compare() indexes the second image's classes by the first's, so
            # it is only defined when the inventories match. Guarded above
            # rather than caught, because a KeyError here would mean the guard
            # was wrong, not that the pair is uninteresting.
            raw = scene_signature.compare(a["boxes"], b["boxes"], False)[0]
            aligned = scene_signature.compare(a["boxes"], b["boxes"], True)[0]
        cross = a["split"] != b["split"]
        rel = REL_LABEL[tuple(sorted((a["split"], b["split"])))] if cross else "same split"
        n_boxes = max(len(a["boxes"]), len(b["boxes"]))
        pairs.append({
            "a": a, "b": b, "cross": cross, "rel": rel,
            "same_multiset": same_multiset, "raw": raw, "aligned": aligned,
            "score": (min(raw, aligned) if same_multiset else None),
            "n_boxes": n_boxes,
            "low": n_boxes <= scene_signature.LOW_INFO_BOX_COUNT,
        })

    cross_pairs = [p for p in pairs if p["cross"]]

    ec61.write_csv(
        os.path.join(run_dir, "consecutive_counter_pairs.csv"),
        ["counter_a", "counter_b", "stem_a", "split_a", "stem_b", "split_b",
         "cross_split", "relationship", "same_class_multiset",
         "raw_max_centre_dist", "aligned_max_centre_dist", "score",
         "n_boxes", "low_information", "file_a", "file_b"],
        [[p["a"]["counter"], p["b"]["counter"], p["a"]["stem"], p["a"]["split"],
          p["b"]["stem"], p["b"]["split"],
          "yes" if p["cross"] else "no", p["rel"],
          "yes" if p["same_multiset"] else "no",
          "" if p["raw"] is None else "%.5f" % p["raw"],
          "" if p["aligned"] is None else "%.5f" % p["aligned"],
          "" if p["score"] is None else "%.5f" % p["score"],
          p["n_boxes"], "yes" if p["low"] else "no",
          p["a"]["file"], p["b"]["file"]]
         for p in pairs])

    # ---- breakdown --------------------------------------------------------
    eps_max = max(scene_signature.EPSILONS)
    breakdown = []
    for rel in RELATIONSHIPS:
        sub = [p for p in cross_pairs if p["rel"] == rel]
        comparable = [p for p in sub if p["same_multiset"]]
        invisible = [p for p in sub if not p["same_multiset"]]
        qualifying = [p for p in comparable if p["score"] is not None
                      and p["score"] <= eps_max and not p["low"]]
        scores = sorted(p["score"] for p in comparable if p["score"] is not None)
        breakdown.append([
            rel, len(sub), len(comparable), len(invisible), len(qualifying),
            "%.4f" % scores[0] if scores else "n/a",
            "%.4f" % scores[len(scores) // 2] if scores else "n/a",
        ])

    ec61.write_csv(
        os.path.join(run_dir, "breakdown_by_relationship.csv"),
        ["relationship", "consecutive_pairs_split_apart",
         "comparable (same multiset)", "never_compared (different multiset)",
         "flagged_as_duplicates", "closest_score", "median_score"],
        breakdown)

    n_same_split = len(pairs) - len(cross_pairs)
    n_invisible_cross = sum(1 for p in cross_pairs if not p["same_multiset"])
    n_flagged = sum(1 for p in cross_pairs
                    if p["same_multiset"] and p["score"] is not None
                    and p["score"] <= eps_max and not p["low"])

    lines = []
    lines.append("# Consecutive counter-number pairs across the released split")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("Reads the released burst-aware tau=15 split. **Changes nothing.**")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["quantity", "value"],
        [["counter-family images", len(recs)],
         ["counter range", "%d - %d" % (counters[0], counters[-1]) if counters else "n/a"],
         ["repeated counter values", len(duplicates)],
         ["pairs differing by exactly 1", len(pairs)],
         ["of those, in the SAME split", n_same_split],
         ["of those, **split apart**", "**%d**" % len(cross_pairs)],
         ["split apart AND never compared (different class multiset)",
          "**%d**" % n_invisible_cross],
         ["split apart AND flagged as duplicates (<= %.2f, low-info excluded)" % eps_max,
          n_flagged]]))
    lines.append("")
    lines.append("## By relationship")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["relationship", "split apart", "comparable", "never compared",
         "flagged as duplicate", "closest", "median"], breakdown))
    lines.append("")
    lines.append("## Every consecutive pair that is split apart")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["counters", "A", "split", "B", "split", "relationship",
         "same multiset", "score"],
        [["%d/%d" % (p["a"]["counter"], p["b"]["counter"]),
          p["a"]["stem"], p["a"]["split"].upper(),
          p["b"]["stem"], p["b"]["split"].upper(), p["rel"],
          "yes" if p["same_multiset"] else "**no**",
          "%.4f" % p["score"] if p["score"] is not None else "**not comparable**"]
         for p in cross_pairs]))
    lines.append("")
    lines.append("## What this does and does not establish")
    lines.append("")
    lines.append("- Consecutive counter numbers mean the camera wrote two files "
                 "in sequence. That makes a burst LIKELY, not certain: a "
                 "photographer can rearrange a scene between two shutter "
                 "presses, and the counter would not know.")
    lines.append("- The `never compared` column is the important one. Those "
                 "pairs have no distance under this method at all, because "
                 "scene_signature only compares images with identical class "
                 "inventories. They are absent from every contamination count "
                 "in this repository -- not scored as safe, simply never "
                 "looked at.")
    lines.append("- A pair scoring above eps was judged not-a-duplicate by "
                 "label geometry. Geometry is a proxy; two frames of one scene "
                 "with a moved component score far apart while looking nearly "
                 "identical to a person.")
    lines.append("- Counter numbers are not globally ordered across devices. "
                 "All %d images here are one family, so adjacency is "
                 "meaningful within it, but a gap in the sequence may mean a "
                 "deleted frame rather than a session boundary." % len(recs))
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    print("  counter images              : %d" % len(recs))
    print("  consecutive pairs (diff 1)  : %d" % len(pairs))
    print("  split apart                 : %d" % len(cross_pairs))
    print("  ... never compared          : %d" % n_invisible_cross)
    print("  ... flagged as duplicates   : %d" % n_flagged)
    for row in breakdown:
        print("  %-14s split_apart=%-3s comparable=%-3s never_compared=%-3s closest=%s"
              % (row[0], row[1], row[2], row[3], row[5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
