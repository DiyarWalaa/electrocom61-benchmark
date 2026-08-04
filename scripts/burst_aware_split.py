"""
burst_aware_split.py -- a CANDIDATE split that moves whole bursts, not images

THE OBJECTION THIS ANSWERS

corrected_split.py minimised images moved and was blind to duplicates. It
moved IMG_20240220_115315 to test and left IMG_20240220_115316 -- shot one
second later, same five components -- in train.

Here the atomic unit of movement is not an image but a GROUP:

  timestamped images -> a burst, from burst_clusters.cluster_by_device at TAU
  untimestamped ones -> a connected component of the near-duplicate graph,
                        from counter_duplicates, since a burst is undefined
                        without a timestamp

Whole groups move together, so a group can never straddle the boundary. The
one-second pair either both go to test or both stay in train.

THIS IS A CANDIDATE, NOT A REPLACEMENT

runs/20260803_corrected_split_02 remains canonical. This run exists to be
compared against it on four numbers: images moved, cross-split near-duplicate
pairs, classes left unrescued, and whether 1478/438/205 survives.

WHY TAU=30 AND NOT SOMETHING SMALLER

runs/20260804_burst_feasibility_02 measured how many distinct groups carry each
never-evaluated class. At tau=10 one class (RFID-Scanner) has only a single
group holding >= 5 instances, so it cannot be given both a valid group and a
test group. At tau=30 every one of the 15 has at least two. Tau=30 is therefore
the smallest swept value at which the whole problem is solvable -- and it costs
something, because bigger tau means bigger groups and the test split only holds
205 images.

WHAT "PURE" MEANS HERE

Only groups lying entirely within one split are eligible to move. A group that
already straddles train and valid in the published data is pre-existing and is
left alone: fixing those is a different question from not creating new ones.
The count of such groups is reported rather than hidden.

HOLDING THE SIZES IS A SUBSET-SUM PROBLEM

Whole-group movement cannot fine-tune a count by one image. Once N images have
been admitted into a split, exactly N must go back, and they must come as whole
groups. That is subset-sum, solved here exactly by dynamic programming over the
available group sizes. If no exact subset exists the script says so and reports
the achieved sizes rather than silently breaking a group to make the number fit.

Run with no arguments:

    python scripts/burst_aware_split.py

Writes runs/<YYYYMMDD>_burst_aware_split/ (auto-suffixed, never overwriting).
"""

import ast
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import burst_clusters  # noqa: E402
import counter_duplicates  # noqa: E402
import scene_signature  # noqa: E402


MIN_PER_SPLIT = 5
TAU = 30                      # see module docstring
SCENE_EPS = 0.05              # loosest epsilon: merges most, safest direction
SEED = 20260804
TARGET_SIZES = {"train": 1478, "valid": 438, "test": 205}
UNTIMESTAMPED = "<untimestamped:counter>"
UNPARSED = "<unparsed-filename>"

BASELINE = "runs/20260803_corrected_split_02"


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def date_bucket(rec):
    if rec.family == "counter":
        return UNTIMESTAMPED
    if rec.date_str:
        return rec.date_str
    return UNPARSED


def read_class_names(data_yaml):
    with open(data_yaml, "r", encoding="utf-8") as fh:
        text = fh.read()
    nc = int(re.search(r"^nc:\s*(\d+)\s*$", text, re.MULTILINE).group(1))
    names = ast.literal_eval(
        re.search(r"^names:\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL).group(1))
    return names, nc


def subset_summing_to(items, target):
    """Exact subset of `items` (index, size) whose sizes sum to `target`.

    Classic subset-sum DP. Returns a list of indices, or None if no exact
    subset exists. Exactness matters: the whole point of the size constraint is
    that it is not approximately satisfied.
    """
    reachable = {0: []}
    for idx, size in items:
        for total in sorted(reachable.keys(), reverse=True):
            new = total + size
            if new <= target and new not in reachable:
                reachable[new] = reachable[total] + [idx]
        if target in reachable:
            return reachable[target]
    return reachable.get(target)


def main():
    run_dir = ec61.make_run_dir("burst_aware_split")
    rng = random.Random(SEED)
    names, nc = read_class_names(os.path.join(ec61.DATASET_DIR, "data.yaml"))

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"tau_seconds": TAU, "scene_epsilon": SCENE_EPS,
                "min_per_split": MIN_PER_SPLIT, "seed": SEED,
                "target_sizes": TARGET_SIZES,
                "unit_of_movement": "whole burst / scene component"},
        extra={"candidate_for": BASELINE,
               "feasibility_basis": "runs/20260804_burst_feasibility_02"},
    )

    records = ec61.load_images()
    by_name = {r.filename: r for r in records}
    boxes_by_name = {r.filename: ec61.load_boxes(r.label_path) for r in records}
    boxes_by_stem = {r.stem: boxes_by_name[r.filename] for r in records}
    published = {r.filename: r.split for r in records}

    img_classes = {}
    for r in records:
        per = {}
        for (cid, _cx, _cy, _w, _h) in boxes_by_name[r.filename]:
            if 0 <= cid < nc:
                per[cid] = per.get(cid, 0) + 1
        img_classes[r.filename] = per

    # ---- build the atomic groups ----------------------------------------
    groups = []   # each: {"images": [...], "splits": set, "per_class": {...}}
    timed = [r for r in records if r.epoch is not None]
    for cl in burst_clusters.cluster_by_device(timed, TAU, lambda r: r.device_key):
        groups.append([r.filename for r in cl])

    counter_recs = [r for r in records if r.family == "counter"]
    if counter_recs:
        pair_rows, _lg = counter_duplicates.score_pairs(counter_recs, boxes_by_stem)
        stem_to_name = {r.stem: r.filename for r in counter_recs}
        edges = [(a, b) for (a, b, _nb, _raw, ali, low, _ri, _ai) in pair_rows
                 if not low and ali <= SCENE_EPS]
        for comp in counter_duplicates.connected_components(
                [r.stem for r in counter_recs], edges):
            groups.append([stem_to_name[s] for s in comp])

    # Any image not captured by either mechanism becomes its own group, so the
    # partition is total and no image can be silently unmovable.
    covered = {f for g in groups for f in g}
    for r in records:
        if r.filename not in covered:
            groups.append([r.filename])

    units = []
    for gid, files in enumerate(groups):
        per_class = {}
        for f in files:
            for cid, n in img_classes[f].items():
                per_class[cid] = per_class.get(cid, 0) + n
        units.append({
            "id": gid,
            "images": sorted(files),
            "n": len(files),
            "splits": {published[f] for f in files},
            "per_class": per_class,
            "dates": sorted({date_bucket(by_name[f]) for f in files}),
        })

    n_straddling = sum(1 for u in units if len(u["splits"]) > 1)

    # ---- deficits ---------------------------------------------------------
    def counts_for(assign):
        c = {i: {s: 0 for s in ec61.SPLITS} for i in range(nc)}
        for f, s in assign.items():
            for cid, n in img_classes[f].items():
                c[cid][s] += n
        return c

    assignment = dict(published)
    counts0 = counts_for(assignment)

    def deficits(assign):
        c = counts_for(assign)
        d = {}
        for i in range(nc):
            for s in ("valid", "test"):
                short = MIN_PER_SPLIT - c[i][s]
                if short > 0:
                    d[(i, s)] = short
        return d

    # ---- admit whole PURE-TRAIN groups -----------------------------------
    pure_train = [u for u in units if u["splits"] == {"train"}]
    rng.shuffle(pure_train)   # seeded tie-break, not filename order

    admitted = {"valid": [], "test": []}
    used = set()
    d = deficits(assignment)
    while d:
        best = None
        for u in pure_train:
            if u["id"] in used:
                continue
            for s in ("test", "valid"):
                val = 0
                for cid, n in u["per_class"].items():
                    need = d.get((cid, s), 0)
                    if need:
                        val += min(n, need)
                if val <= 0:
                    continue
                # Value per image moved: a 40-image burst closing the same
                # deficit as a 3-image burst is a far worse trade, because the
                # size budget is the scarce resource here.
                rank = (-(val / float(u["n"])), u["n"], 0 if s == "test" else 1)
                if best is None or rank < best[0]:
                    best = (rank, u, s)
        if best is None:
            break
        _r, u, s = best
        for f in u["images"]:
            assignment[f] = s
        used.add(u["id"])
        admitted[s].append(u)
        d = deficits(assignment)

    unmet = d

    # ---- return whole groups to train, exact subset-sum -------------------
    returned = {"valid": [], "test": []}
    size_failures = {}
    # Diagnostics: a bare "sizes could not be held" is not a finding. What a
    # reader needs is WHY -- whether there were no safe groups to give back at
    # all, or plenty but none summing exactly to the required total.
    return_pool_stats = {}
    for s in ("valid", "test"):
        need = sum(u["n"] for u in admitted[s])
        if need == 0:
            continue
        # Candidates: groups purely in this split, whose removal keeps every
        # class at or above the bar.
        cur = counts_for(assignment)
        cands = []
        for u in units:
            if u["id"] in used or u["splits"] != {s}:
                continue
            safe = all(cur[cid][s] - n >= MIN_PER_SPLIT
                       for cid, n in u["per_class"].items())
            if safe:
                cands.append(u)
        # How many groups were rejected as unsafe, and why the pool looks as it
        # does. Counted before the subset-sum so the two failure modes -- empty
        # pool vs wrong granularity -- can be told apart.
        n_pure_here = sum(1 for u in units
                          if u["id"] not in used and u["splits"] == {s})
        return_pool_stats[s] = {
            "need": need,
            "pure_groups_in_split": n_pure_here,
            "safe_candidates": len(cands),
            "candidate_images_available": sum(u["n"] for u in cands),
            "candidate_sizes": sorted(u["n"] for u in cands),
        }

        rng.shuffle(cands)
        pick = subset_summing_to([(i, u["n"]) for i, u in enumerate(cands)], need)
        if pick is None:
            size_failures[s] = need
            continue
        for i in pick:
            u = cands[i]
            for f in u["images"]:
                assignment[f] = "train"
            used.add(u["id"])
            returned[s].append(u)

    final_sizes = {s: sum(1 for v in assignment.values() if v == s)
                   for s in ec61.SPLITS}
    counts1 = counts_for(assignment)
    still_short = [(i, s, counts1[i][s]) for i in range(nc)
                   for s in ("valid", "test") if counts1[i][s] < MIN_PER_SPLIT]

    # ---- near-duplicate contamination, same basis as the addendum --------
    buckets = {}
    for r in records:
        buckets.setdefault(
            scene_signature.multiset_key(boxes_by_name[r.filename]), []).append(r.filename)
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

    def contamination(assign, scoring, eps):
        tt = tv = vt = 0
        for (a, b, raw_m, ali_m, low) in scored:
            if low:
                continue
            if (raw_m if scoring == "raw" else ali_m) > eps:
                continue
            sa, sb = assign[a], assign[b]
            if sa == sb:
                continue
            pair = {sa, sb}
            if pair == {"train", "test"}:
                tt += 1
            elif pair == {"train", "valid"}:
                tv += 1
            else:
                vt += 1
        return tt, tv, vt

    contam_rows = []
    for state, assign in (("published", published), ("burst_aware", assignment)):
        for scoring in ("raw", "aligned"):
            for eps in scene_signature.EPSILONS:
                tt, tv, vt = contamination(assign, scoring, eps)
                contam_rows.append([state, scoring, eps, tt, tv, vt, tt + tv + vt])

    # ---- outputs ----------------------------------------------------------
    ec61.write_csv(os.path.join(run_dir, "split_manifest.csv"),
                   ["image_name", "split"],
                   [[f, assignment[f]] for f in sorted(assignment)])

    move_rows = [[f, published[f], assignment[f],
                  date_bucket(by_name[f])]
                 for f in sorted(assignment) if assignment[f] != published[f]]
    ec61.write_csv(os.path.join(run_dir, "moves.csv"),
                   ["image_name", "split_before", "split_after", "capture_date"],
                   move_rows)

    ec61.write_csv(
        os.path.join(run_dir, "groups_moved.csv"),
        ["direction", "split", "group_id", "n_images", "date_groups", "n_classes"],
        [["admitted", s, u["id"], u["n"], ";".join(u["dates"]), len(u["per_class"])]
         for s in ("valid", "test") for u in admitted[s]]
        + [["returned", s, u["id"], u["n"], ";".join(u["dates"]), len(u["per_class"])]
           for s in ("valid", "test") for u in returned[s]])

    ec61.write_csv(
        os.path.join(run_dir, "contamination_comparison.csv"),
        ["state", "scoring", "epsilon", "pairs_train_test", "pairs_train_valid",
         "pairs_valid_test", "pairs_cross_split_total"],
        contam_rows)

    ec61.write_csv(
        os.path.join(run_dir, "class_counts_after.csv"),
        ["class_id", "class_name", "before_valid", "before_test",
         "after_valid", "after_test", "meets_min"],
        [[i, names[i], counts0[i]["valid"], counts0[i]["test"],
          counts1[i]["valid"], counts1[i]["test"],
          "yes" if (counts1[i]["valid"] >= MIN_PER_SPLIT
                    and counts1[i]["test"] >= MIN_PER_SPLIT) else "NO"]
         for i in range(nc)])

    # ---- summary ----------------------------------------------------------
    n_moved = len(move_rows)
    lines = []
    lines.append("# Burst-aware split (CANDIDATE)")
    lines.append("")
    lines.append("Run directory: `%s`  |  tau=%ds  |  scene eps=%.2f  |  seed=%d"
                 % (os.path.basename(run_dir), TAU, SCENE_EPS, SEED))
    lines.append("")
    lines.append("Candidate alternative to `%s`, which remains canonical. "
                 "Whole bursts move together, so no group can straddle the "
                 "split boundary." % BASELINE)
    lines.append("")
    lines.append("## Headline comparison")
    lines.append("")
    ba_raw = [r for r in contam_rows
              if r[0] == "burst_aware" and r[1] == "raw" and r[2] == 0.05][0]
    ba_ali = [r for r in contam_rows
              if r[0] == "burst_aware" and r[1] == "aligned" and r[2] == 0.05][0]
    lines.append(_fmt_markdown_table(
        ["metric", "corrected_split_02", "burst-aware (this run)"],
        [
            ["images moved", 64, n_moved],
            ["test<->train near-dup pairs, raw eps=0.05", 2, ba_raw[3]],
            ["test<->train near-dup pairs, aligned eps=0.05", 4, ba_ali[3]],
            ["classes below the bar", 0, len({c for (c, _s, _n) in still_short})],
            ["sizes held (1478/438/205)", "yes",
             "yes" if final_sizes == TARGET_SIZES else
             "**NO** -> %d/%d/%d" % (final_sizes["train"], final_sizes["valid"],
                                     final_sizes["test"])],
        ]))
    lines.append("")
    lines.append("## Why the size constraint held or failed")
    lines.append("")
    lines.append("To hold the sizes, each split must give back exactly as many "
                 "images as it took, as WHOLE groups. A group can only be given "
                 "back if removing it leaves every class at or above %d."
                 % MIN_PER_SPLIT)
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["split", "images to return", "pure groups in split",
         "safe to remove", "images available in safe groups", "outcome"],
        [[s, st["need"], st["pure_groups_in_split"], st["safe_candidates"],
          st["candidate_images_available"],
          "**failed**" if s in size_failures else "exact subset found"]
         for s, st in sorted(return_pool_stats.items())]))
    lines.append("")
    if size_failures:
        for s in sorted(size_failures):
            st = return_pool_stats[s]
            if st["safe_candidates"] == 0:
                why = ("there is no group in %s that can be removed at all -- "
                       "every one holds the last few instances of some class. "
                       "The split has no slack, not the wrong granularity." % s)
            elif st["candidate_images_available"] < st["need"]:
                why = ("the safe groups hold only %d images between them, fewer "
                       "than the %d required."
                       % (st["candidate_images_available"], st["need"]))
            else:
                why = ("safe groups hold %d images, enough in total, but no "
                       "exact subset sums to %d -- the available group sizes "
                       "(%s) cannot make that number."
                       % (st["candidate_images_available"], st["need"],
                          ", ".join(str(x) for x in st["candidate_sizes"][:20])))
            lines.append("**%s**: %s" % (s, why))
            lines.append("")
    lines.append("## Near-duplicate contamination, three ways")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["state", "scoring", "eps", "test<->train", "valid<->train", "valid<->test"],
        [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in contam_rows]))
    lines.append("")
    lines.append("## Groups")
    lines.append("")
    lines.append("- atomic groups in total: **%d**" % len(units))
    lines.append("- groups already straddling two splits before any move: **%d** "
                 "(left untouched; pre-existing, not created here)" % n_straddling)
    lines.append("- groups admitted: valid %d, test %d"
                 % (len(admitted["valid"]), len(admitted["test"])))
    lines.append("- groups returned to train: valid %d, test %d"
                 % (len(returned["valid"]), len(returned["test"])))
    lines.append("")
    if still_short:
        lines.append("## Classes still below the bar")
        lines.append("")
        lines.append(_fmt_markdown_table(
            ["class", "split", "instances"],
            [[names[c], s, n] for (c, s, n) in still_short]))
        lines.append("")
    if unmet:
        lines.append("Deficits the allocator could not close with whole groups: "
                     "%d." % len(unmet))
        lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- Whole-group movement prevents groups from straddling. It "
                 "does NOT prevent two DIFFERENT groups from being "
                 "near-duplicates of each other; the contamination table above "
                 "is the check on that, not the group logic.")
    lines.append("- tau=%ds was chosen because it is the smallest swept value at "
                 "which every rescued class has two qualifying groups. A larger "
                 "tau would isolate duplicates better and cost more images."
                 % TAU)
    lines.append("- Scene components stand in for bursts among the untimestamped "
                 "images. They group by appearance, not time, and are weaker.")
    lines.append("- Moving more images than the baseline is not automatically "
                 "worse: the two splits should be compared on contamination and "
                 "on class coverage, with images-moved as context.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    print("  images moved      : %d (baseline 64)" % n_moved)
    print("  sizes             : %s" % final_sizes)
    print("  classes short     : %d" % len({c for (c, _s, _n) in still_short}))
    print("  straddling groups : %d (pre-existing)" % n_straddling)
    for r in contam_rows:
        if r[2] == 0.05:
            print("  %-11s %-7s eps=0.05  t<->tr=%d v<->tr=%d v<->te=%d"
                  % (r[0], r[1], r[3], r[4], r[5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
