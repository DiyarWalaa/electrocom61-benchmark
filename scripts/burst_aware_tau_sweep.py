"""
burst_aware_tau_sweep.py -- is there a tau that gives BOTH zero contamination
and the frozen split sizes?

At tau=30 the burst-aware allocator drove test<->train near-duplicate pairs to
zero but could not hold 1478/438/205: test took 20 images and had only 10 it
could safely give back. Smaller tau makes more, smaller groups -- more slack to
return -- but risks leaving a class without two qualifying groups. Larger tau
does the opposite.

This script settles it by running the SAME allocator at each tau and reporting
the three things that decide the question:

  1. do all 15 rescued classes still have >= 2 qualifying groups?
  2. how many test<->train near-duplicate pairs does the result carry?
  3. can 1478/438/205 be held exactly?

WHY THE ALLOCATOR IS IMPORTED, NOT REIMPLEMENTED

`build_units` and `allocate` come from burst_aware_split. A second copy would
be free to drift, and then the sweep and the single-tau run would disagree
without either being obviously wrong. Running this at tau=30 must reproduce
runs/20260804_burst_aware_split_03 exactly, and that is asserted below rather
than assumed.

WHAT "ZERO CONTAMINATION" MEANS HERE

test<->train near-duplicate pairs = 0 at EVERY epsilon under BOTH scorings --
the same bar the published split clears. Zero at eps=0.05 alone would be a
weaker claim, so the strict version is what the decision uses; both are
reported.

The pair scoring does not depend on tau, so it is computed once and reused for
every tau. Only the split assignment changes.

Run with no arguments:

    python scripts/burst_aware_tau_sweep.py

Writes runs/<YYYYMMDD>_burst_aware_tau_sweep/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import scene_signature  # noqa: E402
import burst_aware_split as bas  # noqa: E402


TAUS = (15, 20, 25, 30, 35, 45, 60)
SCENE_EPS = bas.SCENE_EPS
SEED = bas.SEED
MIN_PER_SPLIT = bas.MIN_PER_SPLIT
TARGET_SIZES = bas.TARGET_SIZES

# The tau whose result must reproduce the committed single-tau run, as a check
# that importing the allocator did not change it.
RECONCILE_TAU = 30
RECONCILE_EXPECT = {"train": 1458, "valid": 438, "test": 225}


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("burst_aware_tau_sweep")
    names, nc = bas.read_class_names(os.path.join(ec61.DATASET_DIR, "data.yaml"))

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"taus": list(TAUS), "scene_epsilon": SCENE_EPS, "seed": SEED,
                "min_per_split": MIN_PER_SPLIT, "target_sizes": TARGET_SIZES,
                "zero_contamination_means":
                    "test<->train == 0 at every epsilon under both scorings"},
        extra={"allocator": "imported from burst_aware_split (not reimplemented)",
               "reconciles_with": "runs/20260804_burst_aware_split_03"},
    )

    records = ec61.load_images()
    published = {r.filename: r.split for r in records}
    boxes_by_name = {r.filename: ec61.load_boxes(r.label_path) for r in records}
    boxes_by_stem = {r.stem: boxes_by_name[r.filename] for r in records}
    date_of = {r.filename: bas.date_bucket(r) for r in records}

    img_classes = {}
    for r in records:
        per = {}
        for (cid, _cx, _cy, _w, _h) in boxes_by_name[r.filename]:
            if 0 <= cid < nc:
                per[cid] = per.get(cid, 0) + 1
        img_classes[r.filename] = per

    # never-evaluated classes and train-only groups, both computed
    counts0 = {i: {s: 0 for s in ec61.SPLITS} for i in range(nc)}
    for f, s in published.items():
        for cid, n in img_classes[f].items():
            counts0[cid][s] += n
    never_eval = [i for i in range(nc)
                  if counts0[i]["valid"] == 0 and counts0[i]["test"] == 0]

    group_splits = {}
    for r in records:
        group_splits.setdefault(date_of[r.filename], set()).add(r.split)
    train_only = {g for g, ss in group_splits.items() if ss == {"train"}}

    # ---- score pairs ONCE; independent of tau ----------------------------
    buckets = {}
    for r in records:
        buckets.setdefault(
            scene_signature.multiset_key(boxes_by_name[r.filename]), []
        ).append(r.filename)
    scored = []
    max_eps = max(scene_signature.EPSILONS)
    for key in sorted(buckets, key=str):
        members = sorted(buckets[key])
        if len(members) < 2 or len(members) > scene_signature.MAX_BUCKET:
            continue
        low = sum(c for _cid, c in key) <= scene_signature.LOW_INFO_BOX_COUNT
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                raw = scene_signature.compare(boxes_by_name[a], boxes_by_name[b], False)
                ali = scene_signature.compare(boxes_by_name[a], boxes_by_name[b], True)
                if min(raw[0], ali[0]) > max_eps:
                    continue
                scored.append((a, b, raw[0], ali[0], low))

    def test_train_pairs(assign, scoring, eps):
        n = 0
        for (a, b, raw_m, ali_m, low) in scored:
            if low or (raw_m if scoring == "raw" else ali_m) > eps:
                continue
            if {assign[a], assign[b]} == {"train", "test"}:
                n += 1
        return n

    pair_rows, stem_to_name = bas.counter_pair_rows(records, boxes_by_stem)

    # ---- sweep ------------------------------------------------------------
    rows = []
    detail = []
    reconciled = None
    for tau in TAUS:
        units = bas.build_units(records, img_classes, published, date_of, tau,
                                SCENE_EPS, pair_rows, stem_to_name)

        # Feasibility: qualifying groups per never-evaluated class, counted over
        # groups lying wholly inside the train-only sessions.
        short_classes = []
        for cid in never_eval:
            q = sum(1 for u in units
                    if set(u["dates"]).issubset(train_only)
                    and u["per_class"].get(cid, 0) >= MIN_PER_SPLIT)
            if q < 2:
                short_classes.append("%s(%d)" % (names[cid], q))
        all_feasible = not short_classes

        res = bas.allocate(units, img_classes, published, nc, SEED)
        assign = res["assignment"]
        sizes = {s: sum(1 for v in assign.values() if v == s) for s in ec61.SPLITS}
        sizes_held = (sizes == TARGET_SIZES)
        moved = sum(1 for f in assign if assign[f] != published[f])
        below = len({i for i in range(nc)
                     for s in ("valid", "test")
                     if res["counts_after"][i][s] < MIN_PER_SPLIT})

        tt = {}
        for scoring in ("raw", "aligned"):
            for eps in scene_signature.EPSILONS:
                tt[(scoring, eps)] = test_train_pairs(assign, scoring, eps)
        zero_all = all(v == 0 for v in tt.values())
        zero_05 = (tt[("raw", 0.05)] == 0 and tt[("aligned", 0.05)] == 0)

        if tau == RECONCILE_TAU:
            reconciled = (sizes == RECONCILE_EXPECT)

        rows.append([tau, "yes" if all_feasible else "NO",
                     tt[("raw", 0.05)], tt[("aligned", 0.05)],
                     "yes" if zero_all else "no",
                     "%d/%d/%d" % (sizes["train"], sizes["valid"], sizes["test"]),
                     "yes" if sizes_held else "NO",
                     moved, below,
                     "**YES**" if (zero_all and sizes_held and all_feasible
                                   and below == 0) else "no"])
        detail.append([tau, len(units),
                       sum(1 for u in units if len(u["splits"]) > 1),
                       res["return_pool_stats"].get("test", {}).get("need", 0),
                       res["return_pool_stats"].get("test", {}).get(
                           "candidate_images_available", 0),
                       res["return_pool_stats"].get("valid", {}).get("need", 0),
                       res["return_pool_stats"].get("valid", {}).get(
                           "candidate_images_available", 0),
                       ";".join(short_classes) or "-"])

    ec61.write_csv(
        os.path.join(run_dir, "tau_sweep.csv"),
        ["tau_seconds", "all_15_have_2_qualifying_groups",
         "test_train_pairs_raw_005", "test_train_pairs_aligned_005",
         "zero_at_every_epsilon", "sizes_after", "sizes_held",
         "images_moved", "classes_below_bar", "satisfies_both"],
        rows)

    ec61.write_csv(
        os.path.join(run_dir, "tau_sweep_detail.csv"),
        ["tau_seconds", "n_groups", "n_straddling_groups",
         "test_images_to_return", "test_images_available_to_return",
         "valid_images_to_return", "valid_images_available_to_return",
         "classes_with_fewer_than_2_qualifying_groups"],
        detail)

    winners = [r for r in rows if r[9] == "**YES**"]
    choice = winners[0][0] if winners else None

    lines = []
    lines.append("# Tau sweep: can any tau give zero contamination AND frozen sizes?")
    lines.append("")
    lines.append("Run directory: `%s`  |  seed %d  |  scene eps %.2f"
                 % (os.path.basename(run_dir), SEED, SCENE_EPS))
    lines.append("")
    lines.append("Allocator imported from `burst_aware_split.py`; at tau=%d this "
                 "sweep reproduces `runs/20260804_burst_aware_split_03`: **%s**."
                 % (RECONCILE_TAU, "yes" if reconciled else "NO -- results suspect"))
    lines.append("")
    lines.append("## The answer")
    lines.append("")
    if choice is not None:
        lines.append("**tau = %ds** is the smallest value satisfying both "
                     "conditions." % choice)
    else:
        lines.append("**No tau in the sweep satisfies both.** Zero contamination "
                     "and the frozen 1478/438/205 sizes cannot be had together "
                     "under whole-group movement. The burst-aware split at its "
                     "chosen tau stands as the best available, with the size "
                     "violation reported rather than resolved.")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["tau", "all 15 have >=2 groups", "t<->tr raw .05", "t<->tr aligned .05",
         "zero at every eps", "sizes after", "sizes held", "moved",
         "classes short", "satisfies both"], rows))
    lines.append("")
    lines.append("## Why sizes fail or hold")
    lines.append("")
    lines.append("`test images to return` is what the split owes back; "
                 "`available` is how many sit in groups that can be removed "
                 "without dropping a class below %d." % MIN_PER_SPLIT)
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["tau", "groups", "straddling", "test owes", "test available",
         "valid owes", "valid available", "classes short of 2 groups"], detail))
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- One seed. The allocator is greedy; a different seed explores "
                 "a different corner and could hold sizes where this one fails. "
                 "The sweep answers the question for seed %d." % SEED)
    lines.append("- Feasibility is counted over groups lying wholly inside the "
                 "train-only sessions, matching burst_feasibility. Groups that "
                 "already straddle are excluded from the count.")
    lines.append("- Zero contamination is measured on label geometry, which "
                 "under-detects: an occluded component changes the class "
                 "multiset and the pair is never compared.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    print("  reconciles with committed tau=30 run: %s" % reconciled)
    print("  %-5s %-9s %-8s %-9s %-14s %-7s %s"
          % ("tau", "feasible", "raw.05", "align.05", "sizes", "held", "both"))
    for r in rows:
        print("  %-5s %-9s %-8s %-9s %-14s %-7s %s"
              % (r[0], r[1], r[2], r[3], r[5], r[6], r[9]))
    print("  ANSWER: %s" % ("tau=%d" % choice if choice else "no tau satisfies both"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
