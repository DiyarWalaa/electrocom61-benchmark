"""
corrected_split.py -- STAGE 3: a split where every class is actually evaluable

GOAL
    Every one of the 61 classes holds at least MIN_PER_SPLIT instances in BOTH
    valid and test, while the image counts stay exactly 1478 / 438 / 205.

WHY THE COUNTS ARE HELD FIXED
    If the corrected split also changed the size of the training set, any later
    accuracy difference between this split and the shipped one could be
    attributed to training-set size rather than to split composition. Holding
    1478/438/205 exactly removes that confound: every image admitted to valid
    or test forces one back to train.

WHAT THIS SCRIPT DOES NOT DO
    It moves no files. The output is a manifest (image_name, split). Nothing
    under data/ is written, renamed or deleted.

THE CONFLICT THIS SCRIPT DELIBERATELY RESOLVES IN ONE DIRECTION
    runs/20260802_class_date_provenance established that 15 classes appear only
    in three train-only groups: 20240219 (100 images), 20240220 (486) and the
    189 untimestamped `counter` images. Class coverage therefore REQUIRES
    breaking sessions that session-awareness says to keep whole. Coverage is
    prioritised here by instruction, and the cost is measured rather than
    waved away:

      - how many images were separated from their burst, tau swept
      - the smallest time gap between two images now on opposite sides
      - for the untimestamped images, where time gaps do not exist at all,
        a label-geometry duplicate pass instead

    THE RESULTING SPLIT IS NOT LEAKAGE-FREE. It is the opposite: it manufactures
    cross-split near-duplicates on purpose, because the alternative is 15
    classes that cannot be measured at all. Any per-class score for a rescued
    class carries an optimism caveat, and the manifest flags exactly which
    classes those are so the paper can mark them.

THE MEASUREMENT BLIND SPOT, STATED UP FRONT
    `LED-Light` and `OLED-Display` appear ONLY among the untimestamped images,
    and `Gas-Sensor` and `Sonar-Sensor` partly so. Those filenames encode no
    capture time, so the time-gap cost metric is structurally incapable of
    pricing them. That is why the scene-signature pass exists; it is not a
    refinement, it is the only instrument that can see those four classes.

DETERMINISM
    Greedy selection is deterministic. Ties between equally valuable candidates
    are broken by a seeded permutation (SEED below, recorded in config.json)
    rather than by filename order, because filename order correlates with
    capture date and would silently bias every tie toward the earliest session.

Run with no arguments:

    python scripts/corrected_split.py

Writes runs/<YYYYMMDD>_corrected_split/ (auto-suffixed, never overwriting).
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
# Burst clustering and the duplicate scorer are IMPORTED, never reimplemented.
# If this script defined its own notion of a burst, its cost numbers would not
# reconcile with runs/20260802_burst_clusters and neither could be trusted.
import burst_clusters  # noqa: E402
import scene_signature  # noqa: E402


# The bar every class must clear in valid and in test.
MIN_PER_SPLIT = 5

# Aim for exactly the bar. Targeting a margin would move more images, and every
# extra image moved is extra session damage -- the cost being measured.
TARGET_PER_SPLIT = MIN_PER_SPLIT

# Images may move train <-> valid/test only. Valid <-> test moves are excluded
# so that every change traces back to a train-only session being opened up.
ALLOW_VALID_TEST_MOVES = False

# Seed for tie-breaking only. Recorded in config.json.
SEED = 20260803

# Guard against a pathological repair loop. Reaching this is a reportable
# failure, not something to paper over with a bigger number.
MAX_ITERATIONS = 40

# Tau values for the burst-damage sweep, matching burst_clusters.py so the two
# runs are directly comparable.
TAUS = burst_clusters.TAUS

# Stage-2 artifact this run reconciles against before doing anything else.
STAGE2_COUNTS = os.path.join(
    ec61.RUNS_DIR, "20260802_class_date_provenance", "class_split_counts.csv")

UNTIMESTAMPED = "<untimestamped:counter>"
UNPARSED = "<unparsed-filename>"


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def date_bucket(rec):
    """Capture-date group, with explicit buckets for images that have no date."""
    if rec.family == "counter":
        return UNTIMESTAMPED
    if rec.date_str:
        return rec.date_str
    return UNPARSED


def load_class_names(data_yaml):
    """Read `nc` and `names` from data.yaml (see class_date_provenance.py)."""
    import ast
    import re
    with open(data_yaml, "r", encoding="utf-8") as fh:
        text = fh.read()
    m_nc = re.search(r"^nc:\s*(\d+)\s*$", text, re.MULTILINE)
    if m_nc is None:
        raise ValueError("could not find `nc:` in %s" % data_yaml)
    nc = int(m_nc.group(1))
    m_names = re.search(r"^names:\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL)
    if m_names is None:
        raise ValueError("could not find `names:` in %s" % data_yaml)
    names = ast.literal_eval(m_names.group(1))
    if len(names) != nc:
        raise ValueError("data.yaml disagrees with itself: nc=%d, %d names"
                         % (nc, len(names)))
    return names, nc


def reconcile_with_stage2(counts, names):
    """Cross-check recomputed per-class counts against the Stage-2 CSV.

    The instruction for this stage was to use the committed Stage-2 artifacts.
    Rather than READ counts from that CSV (which would make this run's numbers
    depend on a file with no guarantee it matches today's data/), the counts are
    recomputed here and COMPARED. Agreement means the two runs reconcile;
    disagreement is reported and is a reason to stop, not to continue.

    Returns (n_compared, list_of_mismatches). A missing file is not fatal --
    it is reported as unreconciled.
    """
    import csv
    if not os.path.isfile(STAGE2_COUNTS):
        return 0, [("<file missing>", STAGE2_COUNTS, "", "")]
    mismatches = []
    n = 0
    with open(STAGE2_COUNTS, "r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = int(row["class_id"])
            n += 1
            for split in ec61.SPLITS:
                theirs = int(row["inst_%s" % split])
                ours = counts[cid][split]
                if theirs != ours:
                    mismatches.append((names[cid], split, theirs, ours))
    return n, mismatches


def instance_counts(assignment, img_classes, nc):
    """Per-class instance counts per split under a given assignment.

    assignment  -- {filename: split}
    img_classes -- {filename: {class_id: n_boxes_of_that_class_in_this_image}}
    """
    counts = {c: {s: 0 for s in ec61.SPLITS} for c in range(nc)}
    for fname, split in assignment.items():
        for cid, n in img_classes[fname].items():
            counts[cid][split] += n
    return counts


def deficits_of(counts, nc):
    """{(class_id, split): shortfall} for valid/test, omitting satisfied pairs."""
    out = {}
    for c in range(nc):
        for s in ("valid", "test"):
            short = TARGET_PER_SPLIT - counts[c][s]
            if short > 0:
                out[(c, s)] = short
    return out


def main():
    run_dir = ec61.make_run_dir("corrected_split")
    rng = random.Random(SEED)

    names, nc = load_class_names(os.path.join(ec61.DATASET_DIR, "data.yaml"))

    ec61.write_config(
        run_dir,
        os.path.abspath(__file__),
        params={
            "min_per_split": MIN_PER_SPLIT,
            "target_per_split": TARGET_PER_SPLIT,
            "seed": SEED,
            "seed_role": "tie-breaking among equally valuable candidates only",
            "allow_valid_test_moves": ALLOW_VALID_TEST_MOVES,
            "taus": list(TAUS),
            "max_iterations": MAX_ITERATIONS,
            "frozen_split_sizes": {"train": 1478, "valid": 438, "test": 205},
            "scene_epsilons": list(scene_signature.EPSILONS),
            "scene_low_info_box_count": scene_signature.LOW_INFO_BOX_COUNT,
        },
        extra={
            "stage2_reconciled_against": STAGE2_COUNTS,
            "moves_files": False,
            "output_is": "manifest only (image_name, split)",
        },
    )

    # ----------------------------------------------------------------------
    # Load. Boxes are cached per image because the scene-signature pass at the
    # end needs them again and re-reading 2121 label files would be wasteful.
    # ----------------------------------------------------------------------
    records = ec61.load_images()
    by_name = {r.filename: r for r in records}
    boxes_by_name = {}
    img_classes = {}
    for rec in records:
        boxes = ec61.load_boxes(rec.label_path)
        boxes_by_name[rec.filename] = boxes
        per_class = {}
        for (cid, _cx, _cy, _w, _h) in boxes:
            if 0 <= cid < nc:
                per_class[cid] = per_class.get(cid, 0) + 1
        img_classes[rec.filename] = per_class

    original = {r.filename: r.split for r in records}
    original_sizes = {s: sum(1 for v in original.values() if v == s)
                      for s in ec61.SPLITS}

    counts_before = instance_counts(original, img_classes, nc)
    n_reconciled, mismatches = reconcile_with_stage2(counts_before, names)

    # ----------------------------------------------------------------------
    # Allocation.
    #
    # Two moves alternate until the deficits close:
    #
    #   ADMIT    move a train image into valid or test, chosen to close as much
    #            open deficit as possible in one image.
    #   RETURN   move an equal number of originally-valid / originally-test
    #            images back to train, chosen so that no class falls below the
    #            bar as a result.
    #
    # They alternate rather than running once each because a RETURN can open a
    # new deficit, which then needs another ADMIT. The loop is bounded and
    # reports how many passes it took.
    # ----------------------------------------------------------------------
    assignment = dict(original)
    moved_in = {"valid": [], "test": []}   # train -> here
    moved_out = {"valid": [], "test": []}  # here -> train
    unmet_reason = {}
    iterations = 0

    # Candidate pools, fixed at the start. An image that has already moved is
    # never reconsidered, which guarantees termination.
    train_pool = [f for f, s in original.items() if s == "train"]
    return_pool = {s: [f for f, sp in original.items() if sp == s]
                   for s in ("valid", "test")}
    # Seeded permutation of each pool. Every later sort is stable, so this
    # permutation is what breaks ties -- not alphabetical filename order, which
    # correlates with capture date and would bias ties toward early sessions.
    rng.shuffle(train_pool)
    for s in return_pool:
        rng.shuffle(return_pool[s])

    admitted = set()
    returned = set()

    for iterations in range(1, MAX_ITERATIONS + 1):
        counts_now = instance_counts(assignment, img_classes, nc)
        deficits = deficits_of(counts_now, nc)
        if not deficits:
            break

        # --- ADMIT ---------------------------------------------------------
        # Value of moving image f into split s: how much OPEN deficit it closes.
        # Capped per class at the remaining shortfall, so an image carrying 40
        # instances of one class is not preferred over one covering four
        # classes that each still need instances.
        progress = False
        while deficits:
            best = None
            for f in train_pool:
                if f in admitted:
                    continue
                per_class = img_classes[f]
                if not per_class:
                    continue
                for s in ("test", "valid"):
                    value = 0
                    for cid, n in per_class.items():
                        need = deficits.get((cid, s), 0)
                        if need:
                            value += min(n, need)
                    if value <= 0:
                        continue
                    # Prefer: more deficit closed; then test over valid (test is
                    # the tighter split); then seeded pool order.
                    rank = (-value, 0 if s == "test" else 1)
                    if best is None or rank < best[0]:
                        best = (rank, f, s)
            if best is None:
                break
            _rank, f, s = best
            assignment[f] = s
            admitted.add(f)
            moved_in[s].append(f)
            progress = True
            for cid, n in img_classes[f].items():
                key = (cid, s)
                if key in deficits:
                    deficits[key] -= n
                    if deficits[key] <= 0:
                        del deficits[key]

        if deficits:
            # No remaining train image carries any of these classes.
            for (cid, s), short in deficits.items():
                unmet_reason[(cid, s)] = (
                    "no unmoved train image contains this class; short by %d" % short)

        # --- RETURN --------------------------------------------------------
        # Restore the frozen sizes. For each split, return exactly as many
        # images as were admitted, choosing only images whose removal leaves
        # every class at or above the bar.
        for s in ("valid", "test"):
            need_return = len(moved_in[s]) - len(moved_out[s])
            while need_return > 0:
                counts_now = instance_counts(assignment, img_classes, nc)
                choice = None
                for f in return_pool[s]:
                    if f in returned:
                        continue
                    per_class = img_classes[f]
                    # Slack after removing this image: the smallest margin any
                    # class in it would have left. Negative => unsafe.
                    worst = None
                    for cid, n in per_class.items():
                        margin = counts_now[cid][s] - n - MIN_PER_SPLIT
                        if worst is None or margin < worst:
                            worst = margin
                    if worst is None:
                        # Image contains no annotations at all: removing it can
                        # break nothing, so it is the safest possible choice.
                        worst = 10 ** 6
                    if worst < 0:
                        continue
                    # Prefer the removal that leaves the most slack behind, so
                    # later returns still have safe options available.
                    rank = (-worst,)
                    if choice is None or rank < choice[0]:
                        choice = (rank, f)
                if choice is None:
                    unmet_reason[("<size>", s)] = (
                        "could not return %d image(s) from %s to train without "
                        "pushing some class below %d" % (need_return, s, MIN_PER_SPLIT))
                    break
                _rank, f = choice
                assignment[f] = "train"
                returned.add(f)
                moved_out[s].append(f)
                need_return -= 1
                progress = True

        if not progress:
            break

    counts_after = instance_counts(assignment, img_classes, nc)
    final_sizes = {s: sum(1 for v in assignment.values() if v == s)
                   for s in ec61.SPLITS}

    # Classes still under the bar, with the reason recorded above where known.
    still_short = []
    for c in range(nc):
        for s in ("valid", "test"):
            if counts_after[c][s] < MIN_PER_SPLIT:
                still_short.append((c, s, counts_after[c][s],
                                    unmet_reason.get((c, s), "allocator did not close it")))

    # ----------------------------------------------------------------------
    # Cost: burst damage, before and after.
    #
    # cluster_by_device sorts on rec.epoch, so untimestamped records must be
    # excluded before calling it -- they have epoch None and cannot be placed
    # on a timeline at all. Their count is reported so the exclusion is visible.
    # ----------------------------------------------------------------------
    timed = [r for r in records if r.epoch is not None]
    n_excluded_from_timeline = len(records) - len(timed)

    def burst_rows(tag):
        rows = []
        for tau in TAUS:
            clusters = burst_clusters.cluster_by_device(
                timed, tau, lambda r: r.device_key)
            m = burst_clusters.leakage_metrics(clusters)
            rows.append([tag, tau, m["n_clusters"], m["n_crossing"],
                         m["test_with_train"], m["valid_with_train"],
                         m["largest_cluster"]])
        return rows

    def min_cross_split_gap():
        """Smallest time gap between two images now on opposite sides.

        Only ADJACENT pairs in per-device capture order need checking. If two
        cross-split images have another image between them in time, that middle
        image belongs to one of the two splits, and forms a cross-split pair
        with the other one at a strictly smaller gap. So the global minimum is
        always attained by a temporally adjacent pair.

        Returns (min_gap_seconds, [tightest pairs]) or (None, []) if no
        cross-split adjacency exists.
        """
        by_device = {}
        for r in timed:
            by_device.setdefault(r.device_key, []).append(r)
        pairs = []
        for device in sorted(by_device):
            seq = sorted(by_device[device], key=lambda r: (r.epoch, r.stem))
            for prev, cur in zip(seq, seq[1:]):
                if assignment[prev.filename] != assignment[cur.filename]:
                    pairs.append((cur.epoch - prev.epoch, device,
                                  prev.stem, assignment[prev.filename],
                                  cur.stem, assignment[cur.filename]))
        pairs.sort(key=lambda p: (p[0], p[2], p[4]))
        return (pairs[0][0] if pairs else None), pairs

    before_rows = None
    # Capture "before" metrics while records still hold their original split.
    for r in records:
        r.split = original[r.filename]
    before_rows = burst_rows("before")
    saved_assignment = assignment
    assignment = original
    gap_before, pairs_before = min_cross_split_gap()
    assignment = saved_assignment

    # Switch every record to the new assignment, then remeasure.
    for r in records:
        r.split = assignment[r.filename]
    after_rows = burst_rows("after")
    gap_after, pairs_after = min_cross_split_gap()

    # ----------------------------------------------------------------------
    # Cost: the untimestamped blind spot, via label geometry.
    #
    # Time gaps do not exist for the counter family, so burst damage cannot be
    # measured there at all. Instead: bucket every image by its exact class
    # multiset and score pairs that (a) end up on opposite sides under the new
    # assignment and (b) involve at least one untimestamped image.
    # ----------------------------------------------------------------------
    buckets = {}
    for rec in records:
        key = scene_signature.multiset_key(boxes_by_name[rec.filename])
        buckets.setdefault(key, []).append(rec.filename)

    untimed_names = {r.filename for r in records if r.family == "counter"}
    dup_rows = []
    skipped_buckets = 0
    eps_hits = {e: 0 for e in scene_signature.EPSILONS}
    for key in sorted(buckets, key=lambda k: (len(buckets[k]), str(k))):
        members = sorted(buckets[key])
        if len(members) > scene_signature.MAX_BUCKET:
            # Never silently truncated: a skipped bucket is reported, because
            # "did not look" must not read as "found nothing".
            skipped_buckets += 1
            continue
        n_boxes = sum(c for _cid, c in key)
        low_info = n_boxes <= scene_signature.LOW_INFO_BOX_COUNT
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if assignment[a] == assignment[b]:
                    continue
                if a not in untimed_names and b not in untimed_names:
                    continue
                raw = scene_signature.compare(boxes_by_name[a], boxes_by_name[b], align=False)
                aligned = scene_signature.compare(boxes_by_name[a], boxes_by_name[b], align=True)
                score = min(raw[0], aligned[0])
                if score > max(scene_signature.EPSILONS):
                    continue
                dup_rows.append([a, assignment[a], b, assignment[b],
                                 "%.5f" % raw[0], "%.5f" % aligned[0],
                                 "%.5f" % score, n_boxes,
                                 "yes" if low_info else "no"])
                if not low_info:
                    for e in scene_signature.EPSILONS:
                        if score <= e:
                            eps_hits[e] += 1

    # ----------------------------------------------------------------------
    # Outputs
    # ----------------------------------------------------------------------

    # THE deliverable: image_name, split. Nothing else, so it can be consumed
    # directly without a parser guessing at extra columns.
    ec61.write_csv(
        os.path.join(run_dir, "split_manifest.csv"),
        ["image_name", "split"],
        [[f, assignment[f]] for f in sorted(assignment)],
    )

    # Every move, with the date group it came from.
    move_rows = []
    for f in sorted(assignment):
        if assignment[f] != original[f]:
            rec = by_name[f]
            move_rows.append([f, original[f], assignment[f], date_bucket(rec),
                              rec.device_key, len(boxes_by_name[f])])
    ec61.write_csv(
        os.path.join(run_dir, "moves.csv"),
        ["image_name", "split_before", "split_after", "capture_date",
         "device_key", "n_boxes"],
        move_rows,
    )

    # Per-class instance counts, before and after, both splits.
    cls_rows = []
    for c in range(nc):
        cls_rows.append([
            c, names[c],
            counts_before[c]["train"], counts_before[c]["valid"], counts_before[c]["test"],
            counts_after[c]["train"], counts_after[c]["valid"], counts_after[c]["test"],
            "yes" if (counts_after[c]["valid"] >= MIN_PER_SPLIT
                      and counts_after[c]["test"] >= MIN_PER_SPLIT) else "NO",
            "yes" if (counts_before[c]["valid"] == 0
                      and counts_before[c]["test"] == 0) else "no",
        ])
    ec61.write_csv(
        os.path.join(run_dir, "class_counts_before_after.csv"),
        ["class_id", "class_name",
         "before_train", "before_valid", "before_test",
         "after_train", "after_valid", "after_test",
         "meets_min_after", "was_never_evaluated"],
        cls_rows,
    )

    ec61.write_csv(
        os.path.join(run_dir, "unmet_classes.csv"),
        ["class_id", "class_name", "split", "instances_after", "reason"],
        [[c, names[c], s, n, why] for (c, s, n, why) in still_short],
    )

    # Moves grouped by the date group they came from -- the "which sessions did
    # we have to break" table.
    grp = {}
    for row in move_rows:
        key = (row[3], row[1], row[2])
        grp[key] = grp.get(key, 0) + 1
    ec61.write_csv(
        os.path.join(run_dir, "moves_by_date_group.csv"),
        ["capture_date", "split_before", "split_after", "n_images"],
        [[k[0], k[1], k[2], v] for k, v in sorted(grp.items())],
    )

    # Sessions opened: per source date group, how many images train handed to
    # valid and to test, counted separately.
    #
    # Because valid <-> test moves are disallowed (ALLOW_VALID_TEST_MOVES is
    # False), train is the ONLY path into either split. These two columns
    # therefore account for the entire inflow -- there is no third route a
    # reader needs to go looking for. The share column is what says how far
    # each session was opened: a group that gave up 4% of its images is a
    # different claim from one that gave up half.
    group_train_size = {}
    for rec in records:
        if original[rec.filename] == "train":
            b = date_bucket(rec)
            group_train_size[b] = group_train_size.get(b, 0) + 1

    received = {}
    for row in move_rows:
        _f, sb, sa, bucket = row[0], row[1], row[2], row[3]
        if sb == "train" and sa in ("valid", "test"):
            d = received.setdefault(bucket, {"valid": 0, "test": 0})
            d[sa] += 1

    sessions_rows = []
    for bucket in sorted(received, key=lambda b: (-sum(received[b].values()), b)):
        v, t = received[bucket]["valid"], received[bucket]["test"]
        held = group_train_size.get(bucket, 0)
        sessions_rows.append([
            bucket, held, v, t, v + t,
            "%.1f%%" % (100.0 * (v + t) / held) if held else "n/a",
            held - (v + t),
        ])
    ec61.write_csv(
        os.path.join(run_dir, "sessions_opened.csv"),
        ["capture_date", "images_in_train_before", "to_valid", "to_test",
         "total_released", "share_of_group_released", "remaining_in_train"],
        sessions_rows,
    )

    ec61.write_csv(
        os.path.join(run_dir, "burst_cost_by_tau.csv"),
        ["state", "tau_seconds", "n_clusters", "n_crossing_clusters",
         "test_images_with_train_twin", "valid_images_with_train_twin",
         "largest_cluster"],
        before_rows + after_rows,
    )

    ec61.write_csv(
        os.path.join(run_dir, "cross_split_adjacent_pairs_after.csv"),
        ["gap_seconds", "device_key", "stem_a", "split_a", "stem_b", "split_b"],
        [[int(g), d, sa, spa, sb, spb] for (g, d, sa, spa, sb, spb) in pairs_after[:500]],
    )

    ec61.write_csv(
        os.path.join(run_dir, "untimestamped_duplicate_pairs.csv"),
        ["image_a", "split_a", "image_b", "split_b",
         "raw_max_centre_dist", "aligned_max_centre_dist", "score",
         "n_boxes", "low_information"],
        dup_rows,
    )

    # ----------------------------------------------------------------------
    # summary.md
    # ----------------------------------------------------------------------
    n_moved_total = len(move_rows)
    never_eval_before = [c for c in range(nc)
                         if counts_before[c]["valid"] == 0 and counts_before[c]["test"] == 0]

    lines = []
    lines.append("# Corrected split for ElectroCom61 v2")
    lines.append("")
    lines.append("Run directory: `%s`  |  seed: `%d`" % (os.path.basename(run_dir), SEED))
    lines.append("")
    lines.append("Target: every class holds >= %d instances in BOTH valid and test, "
                 "with image counts frozen at 1478 / 438 / 205." % MIN_PER_SPLIT)
    lines.append("")

    lines.append("## Reconciliation with Stage 2")
    lines.append("")
    if n_reconciled and not mismatches:
        lines.append("All %d classes reconcile with `%s` across all three splits."
                     % (n_reconciled, os.path.basename(STAGE2_COUNTS)))
    elif mismatches:
        lines.append("**%d mismatches against Stage 2** -- results below are suspect:"
                     % len(mismatches))
        lines.append("")
        lines.append(_fmt_markdown_table(["class", "split", "stage 2", "here"],
                                         [list(m) for m in mismatches[:25]]))
    lines.append("")

    lines.append("## Did it work?")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["check", "result"],
        [
            ["image counts train/valid/test",
             "%d / %d / %d %s" % (final_sizes["train"], final_sizes["valid"],
                                  final_sizes["test"],
                                  "(unchanged)" if final_sizes == original_sizes
                                  else "**CHANGED -- constraint violated**")],
            ["classes with >= %d in valid AND test" % MIN_PER_SPLIT,
             "%d of %d" % (nc - len({c for (c, _s, _n, _w) in still_short}), nc)],
            ["classes never evaluable before", len(never_eval_before)],
            ["allocator passes used", iterations],
            ["images moved (total)", n_moved_total],
        ]))
    lines.append("")
    if still_short:
        lines.append("### Classes still below the bar")
        lines.append("")
        lines.append(_fmt_markdown_table(
            ["class_id", "class_name", "split", "instances", "why"],
            [[c, names[c], s, n, why] for (c, s, n, why) in still_short]))
    else:
        lines.append("Every class reaches the bar in both splits.")
    lines.append("")

    lines.append("## Images moved, by date group")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["capture_date", "from", "to", "n_images"],
        [[k[0], k[1], k[2], v] for k, v in sorted(grp.items())]))
    lines.append("")

    lines.append("## Which sessions were opened, and by how much")
    lines.append("")
    lines.append("Valid <-> test moves are disallowed, so train is the only path "
                 "into either split: these columns account for the entire inflow.")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["capture group", "in train before", "-> valid", "-> test",
         "released", "share of group", "left in train"],
        sessions_rows))
    lines.append("")
    lines.append("Totals: valid received **%d** images from train, test received "
                 "**%d** -- %d in all, matched by %d returned to train."
                 % (sum(r[2] for r in sessions_rows),
                    sum(r[3] for r in sessions_rows),
                    sum(r[4] for r in sessions_rows),
                    len([r for r in move_rows if r[2] == "train"])))
    lines.append("")

    lines.append("## Cost: broken bursts")
    lines.append("")
    lines.append("Images excluded from every timeline metric because they carry no "
                 "timestamp: **%d**." % n_excluded_from_timeline)
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["state", "tau", "clusters", "crossing", "test imgs w/ train twin",
         "valid imgs w/ train twin", "largest"],
        before_rows + after_rows))
    lines.append("")

    lines.append("## Cost: smallest cross-split time gap")
    lines.append("")
    lines.append("| state | smallest gap (s) | cross-split adjacent pairs |")
    lines.append("|---|---|---|")
    lines.append("| before | %s | %d |"
                 % ("n/a" if gap_before is None else int(gap_before), len(pairs_before)))
    lines.append("| after | %s | %d |"
                 % ("n/a" if gap_after is None else int(gap_after), len(pairs_after)))
    lines.append("")
    if pairs_after:
        lines.append("Ten tightest pairs after:")
        lines.append("")
        lines.append(_fmt_markdown_table(
            ["gap_s", "device", "stem_a", "split_a", "stem_b", "split_b"],
            [[int(g), d, sa, spa, sb, spb]
             for (g, d, sa, spa, sb, spb) in pairs_after[:10]]))
    lines.append("")

    lines.append("## Cost: the untimestamped blind spot")
    lines.append("")
    lines.append("Time gaps cannot be computed for the `counter` family at all. "
                 "Label-geometry duplicate pairs that end up on opposite sides "
                 "and involve at least one untimestamped image:")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["epsilon", "cross-split near-duplicate pairs (low-information excluded)"],
        [[e, eps_hits[e]] for e in scene_signature.EPSILONS]))
    lines.append("")
    lines.append("Candidate pairs emitted: %d. Buckets skipped as too large: %d."
                 % (len(dup_rows), skipped_buckets))
    lines.append("")

    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- **This split manufactures leakage on purpose.** The 15 rescued "
                 "classes are evaluated on images from the same sessions as their "
                 "training images. Their per-class scores will be optimistic. "
                 "`class_counts_before_after.csv` flags them in "
                 "`was_never_evaluated` so the paper can mark exactly which.")
    lines.append("- Reaching the bar makes a class **measurable, not fairly "
                 "measured**. %d instances is a floor for existence, not a "
                 "sample size anyone should quote a confident AP from."
                 % MIN_PER_SPLIT)
    lines.append("- Greedy allocation is not optimal. A different seed gives a "
                 "different valid split of equal legality; the seed is recorded "
                 "so this one is reproducible, not because it is best.")
    lines.append("- The time-gap metric is blind to the %d untimestamped images. "
                 "The scene-signature pass covers them, but it UNDER-detects by "
                 "construction (an occluded object changes the class multiset and "
                 "the pair is never even considered)." % n_excluded_from_timeline)
    lines.append("- Holding 1478/438/205 removes the training-set-size confound "
                 "but not the composition confound: train's content changed, so "
                 "this split is not a clean A/B against the shipped one either.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    print("  sizes after      : %s (was %s)" % (final_sizes, original_sizes))
    print("  images moved     : %d" % n_moved_total)
    print("  passes           : %d" % iterations)
    print("  classes short    : %d" % len(still_short))
    print("  stage2 mismatches: %d" % len(mismatches))
    print("  min gap before/after: %s / %s" % (gap_before, gap_after))
    print("  untimestamped dup pairs by eps: %s" % (eps_hits,))
    return 0


if __name__ == "__main__":
    sys.exit(main())
