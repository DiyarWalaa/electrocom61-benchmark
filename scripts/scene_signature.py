"""
scene_signature.py -- duplicate detection from YOLO LABEL FILES ONLY

An independent duplicate signal that needs no pixels, no pretrained model and
no downloads: two images of the same scene have (a) the same multiset of class
IDs and (b) boxes in nearly the same places.

Its main value is coverage. Timestamp clustering cannot touch the `counter`
family (IMG_5126 etc.) because those filenames encode no capture time. This
method reaches every annotated image in the dataset.

Two stages:

  A. BUCKET by exact class multiset -- key = sorted (class_id, count) tuple.
     Only images with an identical inventory can be the same scene, so this
     prunes ~2.2M candidate pairs to something small at zero cost.

  B. GEOMETRIC agreement inside each bucket. Boxes are matched per class by
     nearest centre (counts are equal by construction of the key), then scored
     on centre distance and IoU -- in normalised 0-1 coordinates, so the score
     is resolution-independent. This matters because Roboflow stretched every
     image to 640x640.

Scores are computed twice:

  raw       -- centres compared directly. Detects a re-shot static scene.
  aligned   -- each image's mean box centre is subtracted first, making the
               score translation-invariant. Detects a burst where the camera
               drifted, which raw scoring would reject.

Reporting both tells you WHICH kind of duplicate a pair is, not just that it
is one.

Run with no arguments:

    python scripts/scene_signature.py

Writes runs/<YYYYMMDD>_scene_signature/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# A pair is called "same scene" when the WORST matched-box centre distance is
# within epsilon. Using the max rather than the mean is deliberately strict: a
# mean would let one badly displaced object hide behind many well-matched ones.
EPSILONS = (0.01, 0.02, 0.05)

# Pairs inside one bucket grow quadratically. Buckets above this size are
# skipped and reported -- never silently truncated, because a silent cap reads
# as "found nothing" when the truth is "did not look".
MAX_BUCKET = 600

# Buckets with very few boxes carry little geometric information: two images
# each holding a single object of the same class will match on centre distance
# fairly often by chance. Such pairs are still emitted but flagged so they can
# be filtered when quoting a number.
LOW_INFO_BOX_COUNT = 2


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def multiset_key(boxes):
    """Exact class inventory: sorted ((class_id, count), ...).

    Note the conservatism: if one component is occluded in one frame of a
    burst, the counts differ and the pair never becomes a candidate. This
    method therefore UNDER-detects, which is the safe direction for a claim
    that duplicates exist.
    """
    counts = {}
    for cid, _, _, _, _ in boxes:
        counts[cid] = counts.get(cid, 0) + 1
    return tuple(sorted(counts.items()))


def _iou(a, b):
    """IoU of two boxes given as (cx, cy, w, h) in normalised coordinates."""
    ax1, ay1 = a[0] - a[2] / 2.0, a[1] - a[3] / 2.0
    ax2, ay2 = a[0] + a[2] / 2.0, a[1] + a[3] / 2.0
    bx1, by1 = b[0] - b[2] / 2.0, b[1] - b[3] / 2.0
    bx2, by2 = b[0] + b[2] / 2.0, b[1] + b[3] / 2.0
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def _by_class(boxes, offset=(0.0, 0.0)):
    """Group boxes by class id as (cx, cy, w, h), optionally shifting centres."""
    out = {}
    for cid, cx, cy, w, h in boxes:
        out.setdefault(cid, []).append((cx - offset[0], cy - offset[1], w, h))
    return out


def _centroid(boxes):
    """Mean box centre of an image, used for the translation-invariant score."""
    if not boxes:
        return (0.0, 0.0)
    return (sum(b[1] for b in boxes) / len(boxes),
            sum(b[2] for b in boxes) / len(boxes))


def compare(boxes_a, boxes_b, align):
    """Match boxes per class and score the pair.

    Matching is greedy nearest-centre: all candidate pairs within a class are
    sorted by distance and assigned in that order. Object counts per class are
    equal (guaranteed by the bucket key) and are small in this dataset, so
    greedy is effectively optimal here and far cheaper than Hungarian.

    Returns (max_centre_dist, mean_centre_dist, mean_iou).
    """
    off_a = _centroid(boxes_a) if align else (0.0, 0.0)
    off_b = _centroid(boxes_b) if align else (0.0, 0.0)
    ca = _by_class(boxes_a, off_a)
    cb = _by_class(boxes_b, off_b)

    dists = []
    ious = []
    for cid in ca:
        la, lb = ca[cid], cb[cid]
        # Every (i, j) candidate pairing for this class, cheapest first.
        cand = []
        for i, ba in enumerate(la):
            for j, bb in enumerate(lb):
                d = ((ba[0] - bb[0]) ** 2 + (ba[1] - bb[1]) ** 2) ** 0.5
                cand.append((d, i, j))
        cand.sort()
        used_a, used_b = set(), set()
        for d, i, j in cand:
            if i in used_a or j in used_b:
                continue
            used_a.add(i)
            used_b.add(j)
            dists.append(d)
            ious.append(_iou(la[i], lb[j]))

    if not dists:
        return (1.0, 1.0, 0.0)  # nothing to compare -> maximally dissimilar
    return (max(dists), sum(dists) / len(dists), sum(ious) / len(ious))


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("scene_signature")

    records = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    ec61.attach_metadata(records, rows_by_key)

    # ---- load labels ------------------------------------------------------
    boxes_by_stem = {}
    n_no_label_file = 0
    n_empty_label = 0
    usable = []
    for rec in records:
        if rec.label_path is None:
            n_no_label_file += 1
            continue
        boxes = ec61.load_boxes(rec.label_path)
        if not boxes:
            n_empty_label += 1
            continue
        boxes_by_stem[rec.stem] = boxes
        usable.append(rec)

    # ---- stage A: bucket by class multiset --------------------------------
    buckets = {}
    for rec in usable:
        buckets.setdefault(multiset_key(boxes_by_stem[rec.stem]), []).append(rec)

    skipped_buckets = []
    compared_buckets = 0
    n_pairs_examined = 0

    ec61.write_config(
        run_dir,
        __file__,
        params={
            "epsilons": list(EPSILONS),
            "max_bucket": MAX_BUCKET,
            "low_info_box_count": LOW_INFO_BOX_COUNT,
            "matching": "greedy nearest-centre within class",
            "criterion": "max matched-box centre distance <= epsilon",
        },
        extra={
            "n_images_on_disk": len(records),
            "n_with_usable_labels": len(usable),
            "n_missing_label_file": n_no_label_file,
            "n_empty_label_file": n_empty_label,
            "n_buckets": len(buckets),
        },
    )

    # ---- stage B: geometric comparison inside each bucket -----------------
    pair_rows = []
    for key in sorted(buckets, key=lambda k: (-len(buckets[k]), str(k))):
        group = sorted(buckets[key], key=lambda r: r.stem)
        if len(group) < 2:
            continue
        if len(group) > MAX_BUCKET:
            skipped_buckets.append((str(key), len(group)))
            continue
        compared_buckets += 1
        n_boxes = sum(c for _, c in key)
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                n_pairs_examined += 1
                ba, bb = boxes_by_stem[a.stem], boxes_by_stem[b.stem]
                raw_max, raw_mean, raw_iou = compare(ba, bb, align=False)
                ali_max, ali_mean, ali_iou = compare(ba, bb, align=True)
                # Only keep pairs that could matter at the loosest epsilon,
                # under either scoring. Everything tighter is a subset.
                if min(raw_max, ali_max) > max(EPSILONS):
                    continue
                # Time gap where both images are timestamped; blank otherwise.
                if a.epoch is not None and b.epoch is not None:
                    gap = abs(a.epoch - b.epoch)
                else:
                    gap = ""
                pair_rows.append([
                    a.split, b.split, a.stem, b.stem,
                    a.family, b.family, n_boxes,
                    round(raw_max, 5), round(raw_mean, 5), round(raw_iou, 4),
                    round(ali_max, 5), round(ali_mean, 5), round(ali_iou, 4),
                    gap, n_boxes <= LOW_INFO_BOX_COUNT,
                ])

    pair_header = [
        "split_a", "split_b", "stem_a", "stem_b", "family_a", "family_b",
        "n_boxes", "raw_max_dist", "raw_mean_dist", "raw_mean_iou",
        "aligned_max_dist", "aligned_mean_dist", "aligned_mean_iou",
        "time_gap_s", "low_info",
    ]
    ec61.write_csv(os.path.join(run_dir, "scene_pairs.csv"), pair_header, pair_rows)

    cross = [r for r in pair_rows if r[0] != r[1]]
    ec61.write_csv(os.path.join(run_dir, "cross_split_pairs.csv"), pair_header, cross)

    ec61.write_csv(
        os.path.join(run_dir, "skipped_buckets.csv"),
        ["class_multiset", "n_images"],
        skipped_buckets,
    )

    # ---- metrics by epsilon ----------------------------------------------
    # Same headline unit as the burst analysis: TEST IMAGES with a train twin.
    n_test_total = sum(1 for r in usable if r.split == "test")
    metric_rows = []
    for scoring, col in (("raw", 7), ("aligned", 10)):
        for eps in EPSILONS:
            for exclude_low in (False, True):
                test_hits = set()
                valid_hits = set()
                n_pairs = 0
                for row in pair_rows:
                    if exclude_low and row[14]:
                        continue
                    if row[col] > eps:
                        continue
                    n_pairs += 1
                    sa, sb, na, nb = row[0], row[1], row[2], row[3]
                    if sa == "test" and sb == "train":
                        test_hits.add(na)
                    if sb == "test" and sa == "train":
                        test_hits.add(nb)
                    if sa == "valid" and sb == "train":
                        valid_hits.add(na)
                    if sb == "valid" and sa == "train":
                        valid_hits.add(nb)
                metric_rows.append([
                    scoring, eps, exclude_low, n_pairs,
                    len(test_hits), n_test_total,
                    round(100.0 * len(test_hits) / n_test_total, 1) if n_test_total else 0.0,
                    len(valid_hits),
                ])
    ec61.write_csv(
        os.path.join(run_dir, "metrics_by_epsilon.csv"),
        ["scoring", "epsilon", "exclude_low_info", "n_same_scene_pairs",
         "test_images_with_train_twin", "n_test_total", "pct_test",
         "valid_images_with_train_twin"],
        metric_rows,
    )

    # ---- coverage of the images timestamps cannot reach -------------------
    # The whole reason for this method: does it say anything about the
    # `counter` family, which burst_clusters.py must exclude?
    counter_stems = {r.stem for r in usable if r.family == "counter"}
    counter_in_pairs = set()
    for row in pair_rows:
        if row[2] in counter_stems:
            counter_in_pairs.add(row[2])
        if row[3] in counter_stems:
            counter_in_pairs.add(row[3])

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Scene signatures from YOLO labels")
    lines.append("")
    lines.append("Label-only duplicate detection. No pixels, no model, no downloads.")
    lines.append("")
    lines.append("- images on disk: **%d**" % len(records))
    lines.append("- with usable (non-empty) label files: **%d**" % len(usable))
    lines.append("- missing label file: %d; empty label file: %d"
                 % (n_no_label_file, n_empty_label))
    lines.append("- distinct class-multiset buckets: **%d**" % len(buckets))
    lines.append("- buckets compared: %d; pairs examined: %d"
                 % (compared_buckets, n_pairs_examined))
    if skipped_buckets:
        lines.append("- **buckets SKIPPED (over MAX_BUCKET=%d): %d covering %d images**"
                     % (MAX_BUCKET, len(skipped_buckets),
                        sum(n for _, n in skipped_buckets)))
        lines.append("  Coverage is therefore incomplete; see `skipped_buckets.csv`.")
    else:
        lines.append("- buckets skipped: 0 (full coverage of all candidate pairs)")
    lines.append("")

    lines.append("## Same-scene pairs by epsilon")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["scoring", "eps", "excl_low_info", "n_pairs", "test_w_train_twin",
         "n_test", "pct", "valid_w_train_twin"],
        metric_rows))
    lines.append("")
    lines.append("`raw` = centres compared directly (re-shot static scene).")
    lines.append("`aligned` = centroid subtracted first (panned/drifted burst).")
    lines.append("`excl_low_info` drops pairs with <=%d boxes, where a centre match"
                 % LOW_INFO_BOX_COUNT)
    lines.append("is cheap to achieve by chance. Quote the excl_low_info=True row.")
    lines.append("")

    lines.append("## Coverage of the untimestamped `counter` family")
    lines.append("")
    lines.append("- `counter` images with usable labels: **%d**" % len(counter_stems))
    lines.append("- of those, appearing in at least one candidate pair: **%d**"
                 % len(counter_in_pairs))
    lines.append("")
    lines.append("These images carry no timestamp and are invisible to")
    lines.append("`burst_clusters.py`. They sit entirely in train, so they cannot")
    lines.append("leak into test -- but duplicates AMONG them still inflate the")
    lines.append("effective size of the training set relative to its nominal count.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    for name in sorted(os.listdir(run_dir)):
        print("  %s" % name)


if __name__ == "__main__":
    sys.exit(main())