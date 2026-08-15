"""
counter_duplicates.py -- redundancy WITHIN the untimestamped `counter` family

The `counter` family (IMG_5126 etc.) encodes no capture time, so
`burst_clusters.py` cannot see it at all. All 189 of these images sit in
train/, which means they cannot leak into test -- the leakage question is
settled elsewhere and negatively (`scene_signature.py`: zero test images with
a train twin at every epsilon once low-information pairs are excluded).

What they CAN do is inflate the effective size of the training set. If 40 of
the 189 are re-shots of the same few scenes, the paper's nominal train count
overstates how much distinct supervision the model actually received.

WHY THIS SCRIPT EXISTS RATHER THAN QUOTING THE 71

`scene_signature.py` reports "189 counter images, 71 appearing in at least one
candidate pair". That 71 is a loose UPPER BOUND and conflates three things:

  - it counts pairs surviving only the prefilter min(raw, aligned) <= 0.05,
    the loosest epsilon, under whichever scoring happened to be kinder
  - it includes low-information pairs (<= 2 boxes), where a centre match is
    cheap to achieve by chance
  - it includes pairs whose PARTNER is not a counter image

The question actually being asked -- how many of the 189 have a near-duplicate
among the other 188, at excl_low_info=True -- is a strict subset. Both numbers
are printed together so they reconcile instead of appearing to disagree.

PAIRS ARE THE WRONG UNIT; COMPONENTS ARE THE RIGHT ONE

Three images of one scene form three pairs but only two redundant images.
Counting pairs, or even counting images-that-appear-in-a-pair, does not answer
"how much distinct supervision is there". So the near-duplicate relation is
built as a graph over the 189 images and its CONNECTED COMPONENTS are taken:

    effective_unique_scenes = n_components   (singletons included)
    redundant_images        = 189 - n_components

That is the number that belongs in the paper. Note it depends on transitivity:
single-linkage chaining can merge two genuinely different scenes through an
intermediate. Largest component size is reported alongside so that a chained
blob is visible rather than hidden inside a headline.

COVERAGE NOTE

`scene_signature.py` skips buckets larger than MAX_BUCKET (600). Restricted to
the counter family the largest possible bucket is 189, so no cap applies to
the counter-vs-counter analysis and it is exhaustive. The counter-vs-any-train
analysis DOES bucket over all train images and so does inherit the cap; any
skipped bucket is reported.

Scoring is imported from scene_signature rather than reimplemented, so the two
scripts cannot drift apart.

Run with no arguments:

    python scripts/counter_duplicates.py

Writes runs/<YYYYMMDD>_counter_duplicates/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61              # noqa: E402
import scene_signature   # noqa: E402  -- scoring reused, never reimplemented


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def connected_components(nodes, edges):
    """Components of an undirected graph, as a list of sorted node lists.

    Plain BFS over an adjacency map. Isolated nodes come back as singleton
    components, which matters here: the count of components IS the effective
    number of distinct scenes, so images with no duplicate must each count as
    one rather than being dropped.
    """
    adj = {n: set() for n in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    seen = set()
    comps = []
    for start in sorted(nodes):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        comp = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adj[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comps.append(sorted(comp))
    return comps


def score_pairs(group, boxes_by_stem):
    """Score every within-bucket pair of `group`, returning raw rows.

    Returns [(stem_a, stem_b, n_boxes, raw_max, aligned_max, low_info), ...]
    with NO epsilon filtering -- filtering happens per (scoring, epsilon,
    excl_low_info) combination later, so one pass serves the whole sweep.
    """
    rows = []
    buckets = {}
    for rec in group:
        buckets.setdefault(
            scene_signature.multiset_key(boxes_by_stem[rec.stem]), []).append(rec)

    largest_bucket = 0
    for key in sorted(buckets, key=str):
        members = sorted(buckets[key], key=lambda r: r.stem)
        largest_bucket = max(largest_bucket, len(members))
        if len(members) < 2:
            continue
        n_boxes = sum(c for _, c in key)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                ba, bb = boxes_by_stem[a.stem], boxes_by_stem[b.stem]
                raw_max, _, raw_iou = scene_signature.compare(ba, bb, align=False)
                ali_max, _, ali_iou = scene_signature.compare(ba, bb, align=True)
                rows.append((a.stem, b.stem, n_boxes, raw_max, ali_max,
                             n_boxes <= scene_signature.LOW_INFO_BOX_COUNT,
                             raw_iou, ali_iou))
    return rows, largest_bucket


def sweep(all_stems, pair_rows):
    """For each (scoring, epsilon, excl_low_info): pairs, images, components."""
    out = []
    for scoring, idx in (("raw", 3), ("aligned", 4)):
        for eps in scene_signature.EPSILONS:
            for excl_low in (False, True):
                edges = []
                for row in pair_rows:
                    if excl_low and row[5]:
                        continue
                    if row[idx] > eps:
                        continue
                    edges.append((row[0], row[1]))
                in_pair = set()
                for a, b in edges:
                    in_pair.add(a)
                    in_pair.add(b)
                comps = connected_components(all_stems, edges)
                multi = [c for c in comps if len(c) > 1]
                out.append({
                    "scoring": scoring,
                    "epsilon": eps,
                    "exclude_low_info": excl_low,
                    "n_pairs": len(edges),
                    "n_images_with_a_twin": len(in_pair),
                    "n_components": len(comps),
                    "n_multi_components": len(multi),
                    "largest_component": max((len(c) for c in comps), default=0),
                    "redundant_images": len(all_stems) - len(comps),
                })
    return out


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("counter_duplicates")

    records = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    ec61.attach_metadata(records, rows_by_key)

    # Same usability rule as scene_signature: a label file that exists and is
    # non-empty. Applied identically so the two scripts' denominators agree.
    boxes_by_stem = {}
    usable = []
    for rec in records:
        if rec.label_path is None:
            continue
        boxes = ec61.load_boxes(rec.label_path)
        if not boxes:
            continue
        boxes_by_stem[rec.stem] = boxes
        usable.append(rec)

    counter = [r for r in usable if r.family == "counter"]
    counter_stems = sorted(r.stem for r in counter)
    counter_stem_set = set(counter_stems)

    # Sanity: the premise of this script is that the family is train-only.
    counter_splits = {}
    for r in counter:
        counter_splits[r.split] = counter_splits.get(r.split, 0) + 1

    train_usable = [r for r in usable if r.split == "train"]

    # ---- counter vs counter (the question asked) --------------------------
    cc_pairs, cc_largest_bucket = score_pairs(counter, boxes_by_stem)
    cc_sweep = sweep(counter_stems, cc_pairs)

    # ---- counter vs any train image (deliberate widening) -----------------
    # Bucketing spans all train images here, so scene_signature's MAX_BUCKET
    # cap becomes relevant again and skipped buckets must be reported.
    ct_buckets = {}
    for rec in train_usable:
        ct_buckets.setdefault(
            scene_signature.multiset_key(boxes_by_stem[rec.stem]), []).append(rec)
    ct_skipped = []
    ct_pairs = []
    for key in sorted(ct_buckets, key=str):
        members = sorted(ct_buckets[key], key=lambda r: r.stem)
        if len(members) < 2:
            continue
        if len(members) > scene_signature.MAX_BUCKET:
            ct_skipped.append((str(key), len(members)))
            continue
        n_boxes = sum(c for _, c in key)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                # Only pairs touching the counter family are of interest.
                if a.stem not in counter_stem_set and b.stem not in counter_stem_set:
                    continue
                ba, bb = boxes_by_stem[a.stem], boxes_by_stem[b.stem]
                raw_max, _, raw_iou = scene_signature.compare(ba, bb, align=False)
                ali_max, _, ali_iou = scene_signature.compare(ba, bb, align=True)
                ct_pairs.append((a.stem, b.stem, n_boxes, raw_max, ali_max,
                                 n_boxes <= scene_signature.LOW_INFO_BOX_COUNT,
                                 raw_iou, ali_iou))

    ct_rows = []
    for scoring, idx in (("raw", 3), ("aligned", 4)):
        for eps in scene_signature.EPSILONS:
            for excl_low in (False, True):
                hits = set()
                n_pairs = 0
                for row in ct_pairs:
                    if excl_low and row[5]:
                        continue
                    if row[idx] > eps:
                        continue
                    n_pairs += 1
                    if row[0] in counter_stem_set:
                        hits.add(row[0])
                    if row[1] in counter_stem_set:
                        hits.add(row[1])
                ct_rows.append([scoring, eps, excl_low, n_pairs, len(hits)])

    # ---- reconciliation with the 71 ---------------------------------------
    # Reproduce scene_signature's loose prefilter exactly: any pair (counter
    # with anything, any split) where min(raw, aligned) <= max(EPSILONS), low
    # information included.
    loose = set()
    for row in ct_pairs:
        if min(row[3], row[4]) <= max(scene_signature.EPSILONS):
            if row[0] in counter_stem_set:
                loose.add(row[0])
            if row[1] in counter_stem_set:
                loose.add(row[1])
    loose_cc = set()
    for row in cc_pairs:
        if min(row[3], row[4]) <= max(scene_signature.EPSILONS):
            loose_cc.add(row[0])
            loose_cc.add(row[1])

    ec61.write_config(
        run_dir,
        __file__,
        params={
            "epsilons": list(scene_signature.EPSILONS),
            "low_info_box_count": scene_signature.LOW_INFO_BOX_COUNT,
            "max_bucket_applied_to_counter_vs_counter": False,
            "max_bucket_applied_to_counter_vs_train": scene_signature.MAX_BUCKET,
            "scoring_source": "scene_signature.compare (imported, not reimplemented)",
            "redundancy_unit": "connected components (single linkage)",
        },
        extra={
            "n_images_on_disk": len(records),
            "n_usable_labels": len(usable),
            "n_counter_family": len(counter),
            "counter_by_split": counter_splits,
            "n_train_usable": len(train_usable),
            "largest_counter_bucket": cc_largest_bucket,
            "n_counter_vs_counter_pairs_scored": len(cc_pairs),
            "n_counter_vs_train_pairs_scored": len(ct_pairs),
            "n_counter_vs_train_buckets_skipped": len(ct_skipped),
            "loose_prefilter_counter_vs_anything": len(loose),
            "loose_prefilter_counter_vs_counter": len(loose_cc),
        },
    )

    ec61.write_csv(
        os.path.join(run_dir, "counter_vs_counter_metrics.csv"),
        ["scoring", "epsilon", "exclude_low_info", "n_pairs",
         "n_images_with_a_twin", "n_components", "n_multi_components",
         "largest_component", "redundant_images", "n_counter_total"],
        [[d["scoring"], d["epsilon"], d["exclude_low_info"], d["n_pairs"],
          d["n_images_with_a_twin"], d["n_components"], d["n_multi_components"],
          d["largest_component"], d["redundant_images"], len(counter_stems)]
         for d in cc_sweep],
    )

    ec61.write_csv(
        os.path.join(run_dir, "counter_vs_train_metrics.csv"),
        ["scoring", "epsilon", "exclude_low_info", "n_pairs",
         "n_counter_images_with_any_train_twin", "n_counter_total"],
        [r + [len(counter_stems)] for r in ct_rows],
    )

    ec61.write_csv(
        os.path.join(run_dir, "counter_vs_counter_pairs.csv"),
        ["stem_a", "stem_b", "n_boxes", "raw_max_dist", "aligned_max_dist",
         "low_info", "raw_mean_iou", "aligned_mean_iou"],
        [[a, b, n, round(rm, 5), round(am, 5), lo, round(ri, 4), round(ai, 4)]
         for a, b, n, rm, am, lo, ri, ai in
         sorted(cc_pairs, key=lambda x: (min(x[3], x[4]), x[0], x[1]))],
    )

    ec61.write_csv(
        os.path.join(run_dir, "skipped_buckets_counter_vs_train.csv"),
        ["class_multiset", "n_images"],
        ct_skipped,
    )

    # Component membership at the configuration the paper should quote:
    # aligned scoring (tolerates camera drift), excl_low_info=True, swept eps.
    comp_rows = []
    for eps in scene_signature.EPSILONS:
        edges = [(r[0], r[1]) for r in cc_pairs if not r[5] and r[4] <= eps]
        for cid, comp in enumerate(connected_components(counter_stems, edges)):
            if len(comp) < 2:
                continue
            for stem in comp:
                comp_rows.append([eps, cid, len(comp), stem])
    ec61.write_csv(
        os.path.join(run_dir, "counter_components_aligned_excl_low.csv"),
        ["epsilon", "component_id", "component_size", "stem"],
        comp_rows,
    )

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Redundancy within the untimestamped `counter` family")
    lines.append("")
    lines.append("- `counter` images with usable labels: **%d**" % len(counter))
    lines.append("- their actual directories: %s"
                 % ", ".join("%s=%d" % (s, counter_splits.get(s, 0))
                             for s in ec61.SPLITS))
    lines.append("- largest class-multiset bucket inside the family: %d "
                 "(MAX_BUCKET=%d never binds, so this is exhaustive)"
                 % (cc_largest_bucket, scene_signature.MAX_BUCKET))
    lines.append("- counter-vs-counter pairs scored: %d" % len(cc_pairs))
    lines.append("")
    lines.append("These images cannot leak into test -- they are all in train, and")
    lines.append("`scene_signature.py` finds zero test images with a train twin at")
    lines.append("every epsilon with low-information pairs excluded. What follows is")
    lines.append("about TRAINING SET SIZE, not contamination.")
    lines.append("")

    lines.append("## Counter vs counter: how many of the %d have a twin among the "
                 "other %d" % (len(counter), len(counter) - 1))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["scoring", "eps", "excl_low", "n_pairs", "imgs_with_twin",
         "components", "multi_comps", "largest_comp", "redundant"],
        [[d["scoring"], d["epsilon"], d["exclude_low_info"], d["n_pairs"],
          d["n_images_with_a_twin"], d["n_components"], d["n_multi_components"],
          d["largest_component"], d["redundant_images"]] for d in cc_sweep]))
    lines.append("")
    lines.append("`components` counts distinct scenes, singletons included, so it is")
    lines.append("the effective number of independent training images in this family.")
    lines.append("`redundant` = %d - components. Quote that, not `imgs_with_twin`:"
                 % len(counter))
    lines.append("three shots of one scene make 3 pairs and 3 images-with-a-twin but")
    lines.append("only 2 redundant images.")
    lines.append("")
    lines.append("Single linkage is transitive, so a large `largest_comp` may be a")
    lines.append("chain through intermediates rather than one repeated scene. Check")
    lines.append("`counter_components_aligned_excl_low.csv` before quoting a large one.")
    lines.append("")

    lines.append("## Counter vs ANY train image (wider than the question asked)")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["scoring", "eps", "excl_low", "n_pairs", "counter_imgs_with_train_twin"],
        ct_rows))
    lines.append("")
    if ct_skipped:
        lines.append("**%d bucket(s) skipped (over MAX_BUCKET=%d), covering %d "
                     "images.** This table is therefore a LOWER bound; the "
                     "counter-vs-counter table above is not affected."
                     % (len(ct_skipped), scene_signature.MAX_BUCKET,
                        sum(n for _, n in ct_skipped)))
    else:
        lines.append("No bucket exceeded MAX_BUCKET=%d; this table is complete."
                     % scene_signature.MAX_BUCKET)
    lines.append("")

    lines.append("## Reconciling with the `71` in the scene_signature summary")
    lines.append("")
    lines.append("- counter images in >=1 pair with ANYTHING, loose prefilter "
                 "min(raw,aligned)<=%.2f, low-info included: **%d**"
                 % (max(scene_signature.EPSILONS), len(loose)))
    lines.append("- same, restricted to counter-vs-counter: **%d**" % len(loose_cc))
    lines.append("")
    lines.append("The scene_signature figure is an upper bound built on the loosest")
    lines.append("epsilon, the kinder of the two scorings, and pairs with any")
    lines.append("partner. The tables above are the strict readings of it.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    for name in sorted(os.listdir(run_dir)):
        print("  %s" % name)


if __name__ == "__main__":
    sys.exit(main())